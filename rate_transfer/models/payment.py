from odoo import models, fields, api


class payment(models.Model):
    _inherit = "account.payment"
    jornal = fields.Many2one(comodel_name="res.currency", string="Jornal", store=True)
    rate = fields.Monetary(string="Rate", currency_field='jornal')
    transfer_money = fields.Monetary(currency_field='jornal', compute="_compute_money")
    assign_2 = fields.Many2one('res.users', string="Assign-2")

    @api.onchange('amount', 'transfer_money', 'jornal')
    def _compute_money(self):
        self.transfer_money = (self.amount * self.jornal.rate) + self.rate
