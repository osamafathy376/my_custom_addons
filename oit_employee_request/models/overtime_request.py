# -*- coding: utf-8 -*-آ1ى1

# Copyright 2021 Ahmed Amen :  www.linkedin.com/in/ahmed-abdul-khaliq
##############################################################################
from odoo import _, api, fields, models,exceptions


class overtime_request(models.Model):
    _name = "overtime.request"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    def unlink(self):
        if any(rec.state != 'draft' for rec in self):
            raise exceptions.ValidationError(_('You cannot delete records if they are in non-draft state'))
        return super(overtime_request, self).unlink()

    name = fields.Char(string="Request", readonly=True)
    employee_id = fields.Many2one(comodel_name="hr.employee", required=True, string="Employee",readonly=True, states={'draft': [('readonly', False)]},)
    request_date = fields.Date(string="Request Date", required=True, track_visibility='always',readonly=True, states={'draft': [('readonly', False)]}, )

    contract_id = fields.Many2one(comodel_name="hr.contract", string="Contract", related="employee_id.contract_id",
                                  required=True, track_visibility='always', )
    contract_start_date = fields.Date(string="Contract Start Date", related="contract_id.first_contract_date",
                                      track_visibility='always', )
    basic_salary = fields.Float(string="Basic Salary", track_visibility='always', compute="get_basic_salary")

    gross = fields.Float(string="Gross", track_visibility='always', compute="cal_gross_amt")
    alwns_amount = fields.Float(string="Allowances", track_visibility='always', compute="cal_alwns_amt")
    loan_status = fields.Selection(string="Loan status", related="employee_id.loan_status", )


    extra_hours = fields.Float(string="Normal Extra Hours",readonly=True, states={'draft': [('readonly', False)]},)
    extra_hours_vacation = fields.Float(string="Weekend and Public Holiday Extra Hours",readonly=True, states={'draft': [('readonly', False)]},)
    hour_value = fields.Float(string="Hour Value", compute="com_hours_value",)
    extra_day_value = fields.Float(string="Normal Extra Value",compute="com_hours_value")
    extra_day_value_vacation = fields.Float(string="Weekend and Public Holiday Extra Value",compute="com_hours_value")
    total_hours_due = fields.Float(string="Total Hours Value",compute="com_hours_value")

    state = fields.Selection(string="State", selection=[('draft', 'Draft'), ('confirm', 'Confirm'), ('paid', 'Paid'), ],
                             default="draft", required=False, )

    debit_account_id = fields.Many2one('account.account', 'Debit Account', track_visibility='always', readonly=True,
                                       states={'draft': [('readonly', False)]},
                                       default=lambda self: self.env['res.config.settings'].sudo().browse(
                                           self.env['res.config.settings'].sudo().search([])[
                                               -1].id).req_leave_acc_debit_id.id if self.env[
                                           'res.config.settings'].sudo().search([]) else "")
    credit_account_id = fields.Many2one('account.account', 'Credit Account', track_visibility='always', readonly=True,
                                        states={'draft': [('readonly', False)]},
                                        default=lambda self: self.env['res.config.settings'].sudo().browse(
                                            self.env['res.config.settings'].sudo().search([])[
                                                -1].id).req_leave_acc_credit_id.id if self.env[
                                            'res.config.settings'].sudo().search([]) else "")
    journal_id = fields.Many2one('account.journal', 'Journal', track_visibility='always', readonly=True,
                                 states={'draft': [('readonly', False)]},
                                 default=lambda self: self.env['res.config.settings'].sudo().browse(
                                     self.env['res.config.settings'].sudo().search([])[
                                         -1].id).req_leave_journal_id.id if
                                 self.env['res.config.settings'].sudo().search([]) else "")
    pay_journal_id = fields.Many2one('account.journal', 'Payment Journal', readonly=True,
                                     states={'confirm': [('readonly', False)]},
                                     domain=[('type', 'in', ('bank', 'cash'))])


    move_ids = fields.Many2many(comodel_name="account.move", string="Moves", readonly=True)
    move_count = fields.Integer(string="Moves", compute="com_move_count", required=False, )

    def com_move_count(self):
        for rec in self:
            rec.move_count = len(self.move_ids.ids)

    def button_journal_entries(self):
        return {
            'name': _('Journal Entries'),
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'search_view_id': [self.env.ref('account.view_account_move_filter').id, 'search'],
            'views': [(self.env.ref('account.view_move_tree').id, 'tree'), (False, 'form')],
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', self.move_ids.ids)],
            'context': dict(self._context, create=False),
        }

    def confirm_entry(self):
        account_move_obj = self.env['account.move']
        if self.employee_id.address_home_id:
            partner = self.employee_id.address_home_id
        elif self.employee_id.user_id:
            partner = self.employee_id.user_id.partner_id
        else:
            raise exceptions.ValidationError("The Employee Doesn't Have Partner")

        if not self.debit_account_id:
            raise exceptions.ValidationError("Debit Account Can't Be Null")

        if not self.journal_id:
            raise exceptions.ValidationError("Default Journal Can't Be Null")

        vals = []
        price = self.total_hours_due
        if not price:
            raise exceptions.ValidationError("Can't Conform with 0.0 Amount")
        ref = 'OverTime Request# ' + self.name
        if price:
            vals.append((0, 0, {

                'name': ref,
                'partner_id': partner.id,
                'account_id': self.debit_account_id.id,
                'debit': price,
                'credit': 0.0}))
            vals.append((0, 0, {'name': ref,
                                'partner_id': partner.id,
                                'account_id': self.credit_account_id.id,
                                'debit': 0.0,
                                'credit': price}))

        move = account_move_obj.create(
            {'date': self.request_date, 'ref': ref, 'journal_id': self.journal_id.id, 'move_type': 'entry',
             'line_ids': vals})
        print("move ==> ", move)
        move.sudo().action_post()
        self.move_ids = [(4, move.id)]

    def pay_entry(self):
        account_move_obj = self.env['account.move']
        if self.employee_id.address_home_id:
            partner = self.employee_id.address_home_id
        elif self.employee_id.user_id:
            partner = self.employee_id.user_id.partner_id
        else:
            raise exceptions.ValidationError("The Employee Doesn't Have Partner")

        if not self.credit_account_id:
            raise exceptions.ValidationError("Credit Account Can't Be Null")

        if not self.pay_journal_id :
            raise exceptions.ValidationError("Payment Journal Can't Be Null")

        vals = []
        price = self.total_hours_due
        if not price:
            raise exceptions.ValidationError("Can't Conform with 0.0 Amount")
        ref = 'OverTime Request# ' + self.name,
        if price:
            vals.append((0, 0, {'name': ref,
                                'partner_id': partner.id,
                                'account_id': self.pay_journal_id.default_account_id.id,
                                'debit': 0.0,
                                'credit': price}))
            vals.append((0, 0, {'name': ref,
                                'partner_id': partner.id,
                                'account_id': self.credit_account_id.id,
                                'debit': price,
                                'credit': 0.0}))

        move = account_move_obj.create(
            {'date': self.request_date, 'ref': ref, 'journal_id': self.pay_journal_id.id, 'move_type': 'entry',
             'line_ids': vals})
        print("move ==> ", move)
        move.sudo().action_post()
        self.move_ids = [(4, move.id)]

    def action_confirm(self):
        for rec in self:
            if rec.state == 'draft':
                rec.confirm_entry()
                rec.state = 'confirm'

    def action_paid(self):
        for rec in self:
            if rec.state == 'confirm':
                rec.pay_entry()
                rec.state = 'paid'



    @api.model
    def create(self, values):
        values['name'] = self.env['ir.sequence'].next_by_code('overtime.order') or _('New')
        return super(overtime_request, self).create(values)

    @api.depends('employee_id','basic_salary','extra_hours_vacation','extra_hours')
    def com_hours_value(self):
        for rec in self:
            ret = rec.basic_salary/280
            day_value = ret * rec.extra_hours * 1.5
            leave_day_value = ret * rec.extra_hours_vacation * 2
            rec.hour_value = ret
            rec.extra_day_value = day_value
            rec.extra_day_value_vacation = leave_day_value
            rec.total_hours_due = day_value + leave_day_value

    @api.depends('contract_id')
    def cal_gross_amt(self):
        for rec in self:
            payslip = self.env['hr.payslip.line'].sudo().search(
                [('employee_id', '=', rec.employee_id.id), ('slip_id.state', '=', 'done'), ('code', '=', 'GROSS')],
                limit=1, order='id DESC')

            rec.gross = payslip.total or 0.0

    @api.depends('contract_id')
    def cal_alwns_amt(self):
        for rec in self:
            alw_catg = self.env['hr.salary.rule.category'].sudo().search([('code', '=', 'ALW')], limit=1,
                                                                         order='id DESC')
            payslip = self.env['hr.payslip'].sudo().search(
                [('employee_id', '=', rec.employee_id.id), ('state', '=', 'done')],
                limit=1, order='id DESC')
            alw_lines = payslip.line_ids.filtered(lambda record: record.category_id.id == alw_catg.id)
            if alw_lines:
                amt = sum(alw_lines.mapped('total'))
            else:
                amt = 0.0

            rec.alwns_amount = amt

    @api.depends('employee_id')
    def get_basic_salary(self):
        for rec in self:
            contract = self.env['hr.contract']
            if rec.employee_id:
                if rec.employee_id.contract_ids:
                    contract = rec.employee_id.contract_ids[0]
                else:
                    contract = rec.employee_id.contract_id
            if contract:
                rec.basic_salary = contract.wage
            else:
                rec.basic_salary = 0.0

