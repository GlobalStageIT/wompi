import logging
import uuid
import requests
from werkzeug import urls

from odoo import api, models, _
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_compare

from odoo.addons.payment_wompi.controllers.main import WompiController


_logger = logging.getLogger(__name__)


class PaymentTransactionWompi(models.Model):
    _inherit = 'payment.transaction'
 
    @api.model
    def _get_specific_rendering_values(self, processing_values):
        res = super()._get_specific_processing_values(processing_values)
        if self.provider != 'wompi':
            return res

        tx = self.env['payment.transaction'].search([('reference', '=', processing_values.get('reference'))])
        # wompi will not allow any payment twice even if payment was failed last time.
        # so, replace reference code if payment is not done or pending.
        if tx.state not in ['done', 'pending']:
            tx.reference = str(uuid.uuid4())

        api_url = 'https://checkout.wompi.co/p/' \
            if self.acquirer_id.state == 'enabled' \
            else 'https://checkout.wompi.co/p/'
        acquirer = self.acquirer_id
        wompi_values = dict(
            processing_values,
            merchantId=acquirer.wompi_prod_merchant_id if self.state == 'prod' else acquirer.wompi_test_merchant_id,
            description=processing_values.get('reference'),
            referenceCode=tx.reference,
            amount=int(processing_values['amount']) * 100,
            tax='0',  # This is the transaction VAT. If VAT zero is sent the system, 19% will be applied automatically. It can contain two decimals. Eg 19000.00. In the where you do not charge VAT, it should should be set as 0.
            taxReturnBase='0',
            currency=self.env['res.currency'].browse(processing_values['currency_id']).name,
            buyerEmail=self.env['res.partner'].browse(processing_values['partner_id']).email,
            api_url=api_url,
            tx_url=api_url,
            responseUrl=urls.url_join(self.get_base_url(), WompiController._return_url),
        )
        if acquirer.state != 'enabled':
            wompi_values['test'] = 1
        wompi_values['signature'] = acquirer._wompi_generate_sign(wompi_values, incoming=False)
        wompi_values['referenceCode'] = f"{wompi_values['referenceCode']}|{wompi_values['signature']}"
        
        return wompi_values


    def _wompi_get_feedback_data(self, acquirer, data):
        if acquirer.state == 'test':
            url = f'https://sandbox.wompi.co/v1/transactions/{data.get("id")}'
        else:
            url = f'https://production.wompi.co/v1/transactions/{data.get("id")}'

        resp = requests.get(url)
        if resp.status_code != 200:
            raise ValidationError(_("Wompi service unavailable"))
        else:
            data = resp.json()['data']
        return data

    @api.model
    def _get_tx_from_feedback_data(self, provider, data):
        """ Override of payment to find the transaction based on Wompi data.

        :param str provider: The provider of the acquirer that handled the transaction
        :param dict data: The feedback data sent by the provider
        :return: The transaction if found
        :rtype: recordset of `payment.transaction`
        :raise: ValidationError if inconsistent data were received
        :raise: ValidationError if the data match no transaction or more than one transaction
        :raise: ValidationError if the signature can not be verified
        """
        tx = super()._get_tx_from_feedback_data(provider, data)
        if provider != 'wompi':
            return tx

        acquirer = self.env['payment.acquirer'].search([('provider', '=', 'wompi')])
        data = self._wompi_get_feedback_data(acquirer, data)

        reference = data.get('reference')
        reference, sign = reference.split("|")[0].strip(), reference.split("|")[1].strip()
        if not reference or not sign:
            error_message = _('Wompi: received data with missing reference (%s) or sign (%s)') % (reference, sign)
            _logger.error(error_message)
            return False

        tx = self.search([('reference', '=', reference), ('acquirer_id', '=', acquirer.id)])
        if not tx:
            error_message = (_('Wompi: received data for reference %s; no order found') % (reference))
            tx._set_error("Wompi: " + error_message)
            return tx
        elif len(tx) > 1:
            error_message = (_('Wompi: received data for reference %s; multiple orders found') % (reference))
            _logger.error(error_message)
            tx._set_error(error_message)
            return tx
    
        invalid_parameters = tx._wompi_form_get_invalid_parameters(data)
        if invalid_parameters:
            error_message = _('Wompi: incorrect tx data:\n')
            for item in invalid_parameters:
                error_message += _('\t%s: received %s instead of %s\n' % (item[0], item[1], item[2]))
            _logger.error(error_message)
            tx._set_error(error_message)
            return tx

        # Verify signature
        data_wompi = {
            "referenceCode": reference,
            "amount": data.get("amount_in_cents"),
            "currency": data.get("currency"),
            "transactionState": data.get("status"),
            "TX_VALUE": data.get("amount_in_cents"),
        }
        sign_check = tx.acquirer_id._wompi_generate_sign(data_wompi, incoming=True)
        if sign_check.upper() != sign.upper():
            error_message = _('Wompi: invalid sign, received %s, computed %s') % (sign, sign_check)
            _logger.error(error_message + f" for data {data}")
            tx._set_error(error_message)
            return tx
        tx._wompi_process_feedback_data(data)
        return tx

    def _wompi_form_get_invalid_parameters(self, data):
        invalid_parameters = []

        if float_compare(float(data.get('amount_in_cents', '0.0') / 100) , self.amount, 2) != 0:
            invalid_parameters.append(('Amount', data["data"].get('amount_in_cents') / 100, '%.2f' % self.amount))

        return invalid_parameters

    def _wompi_process_feedback_data(self, data):
        super()._process_feedback_data(data)
        if self.provider != 'wompi':
            return

        status = data.get('status')
        res = {
            'acquirer_reference': data.get('id'),
        }
        state_message = status or ""

        if status == 'APPROVED':
            _logger.info('Validated Wompi payment for tx %s: set as done' % (self.reference))
            self._set_done(state_message=state_message)
        elif status == 'PENDING':
            _logger.info('Received notification for Wompi payment %s: set as pending' % (self.reference))
            self._set_pending(state_message=state_message)
        elif status in ['VOIDED', 'DECLINED']:
            _logger.info('Received notification for Wompi payment %s: set as Cancel' % (self.reference))
            self._set_canceled(state_message=state_message)
        else:
            error = 'Received unrecognized status for Wompi payment %s: %s, set as error' % (self.reference, status)
            _logger.error(error)
            self._set_error("Wompi: " + _("Invalid payment status."))

        self.write(res)
