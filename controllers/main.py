import logging
import pprint

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class WompiController(http.Controller):
    _return_url = '/payment/wompi/return'

    @http.route(_return_url, type='http', auth='public', methods=['GET'])
    def wompi_return(self, **data):
        _logger.info("Wompi: entering _handle_feedback_data with data:\n%s", pprint.pformat(data))
        request.env['payment.transaction'].sudo()._handle_feedback_data('wompi', data)
        return request.redirect('/payment/status')
