odoo.define('payment_wompi.payment_form', require => {
    'use strict';

    const checkoutForm = require('payment.checkout_form');

    const wompiPaymentForm = {
        _processRedirectPayment: function (provider, acquirerId, processingValues) {
            if (provider !== 'wompi') {
                return this._super(...arguments);
            }
            const $redirectForm = $(processingValues.redirect_form_html).attr(
                'id', 'o_payment_redirect_form'
            );
            $(document.getElementsByTagName('body')[0]).append($redirectForm);
            $redirectForm.attr("action", $redirectForm.find('input[name="data_set"]').val());
            $redirectForm.submit();
        },
    };

    checkoutForm.include(wompiPaymentForm);

});
