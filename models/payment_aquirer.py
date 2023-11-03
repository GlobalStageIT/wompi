import logging
from hashlib import md5

from odoo import fields, models, _


class PaymentAcquirer(models.Model):
    _inherit = 'payment.acquirer'

    provider = fields.Selection(selection_add=[
        ('wompi', 'Wompi Bancolombia')
    ], ondelete={'wompi': 'set default'})
    wompi_prod_merchant_id = fields.Char(string="Wompi public-key(Prod)", required_if_provider='wompi', groups='base.group_user')
    wompi_test_merchant_id = fields.Char(string="Wompi public-key(Test)", required_if_provider='wompi', groups='base.group_user')


    def _wompi_generate_sign(self, values, incoming=True):
        if incoming:
            data_string = ('~').join((self.wompi_prod_merchant_id if self.state == 'prod' else self.wompi_test_merchant_id, values['referenceCode'],
                                      str(values.get('TX_VALUE')), values['currency']))
        else:
            data_string = ('~').join((self.wompi_prod_merchant_id if self.state == 'prod' else self.wompi_test_merchant_id, values['referenceCode'],
                            str(values['amount']), values['currency']))
            
        return md5(data_string.encode('utf-8')).hexdigest()
    
    def _get_default_payment_method_id(self):
        self.ensure_one()
        if self.provider != 'wompi':
            return super()._get_default_payment_method_id()
        return self.env.ref('payment_wompi.payment_method_wompi').id


