# -*- coding: utf-8 -*-آ1ى1

# Copyright 2021 Ahmed Amen :  www.linkedin.com/in/ahmed-abdul-khaliq
##############################################################################
from odoo import _, api, fields, models,exceptions


class leave_request(models.Model):
    _name = "leave.request"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    def unlink(self):
        if any(rec.state != 'draft' for rec in self):
            raise exceptions.ValidationError(_('You cannot delete records if they are in non-draft state'))
        return super(leave_request, self).unlink()

    name = fields.Char(string="leave", readonly=True)
    employee_id = fields.Many2one(comodel_name="hr.employee",required=True,  string="Employee",readonly=True, states={'draft': [('readonly', False)]},)
    request_date = fields.Date(string="Request Date", required=True,track_visibility='always', readonly=True, states={'draft': [('readonly', False)]},)

    jouin_date = fields.Date(string="Joining Date",related="employee_id.jouin_date",  required=False,track_visibility='always', )
    return_date_lst_lev = fields.Date(string="Return Date of Last Leave",related="employee_id.return_date_lst_lev", track_visibility='always', )

    leave_entitlement = fields.Selection(string="Leave Entitlement",related="employee_id.leave_entitlement", track_visibility='always',
                                         selection=[('yearly', 'Yearly'), ('2 years', '2 Years')])

    annual_leave_days = fields.Integer(string="Annual Leave Days",related="employee_id.annual_leave_days", track_visibility='always',)
    number_of_days_due = fields.Integer(string="Due Days Number",track_visibility='always',readonly=True, states={'draft': [('readonly', False)]},)
    value_of_days_due = fields.Float(string="Due Days Value" , track_visibility='always',compute="compute_due_days_value")
    basic_salary = fields.Float(string="Basic Salary", track_visibility='always', compute="get_basic_salary")

    travel_ticket_value = fields.Float(string="Travel Ticket Value", related="employee_id.travel_ticket_value",readonly=False,
                                       track_visibility='always', )
    period_of_leave_due = fields.Char(string="period Of leave due",track_visibility='always',compute="cal_period_of_leave_due")
    note = fields.Text(string="Note",readonly=True, track_visibility='always',states={'draft': [('readonly', False)]},)
    total_allowance_value = fields.Float(string="Total Allowance Value",track_visibility='always',compute="compute_allowance_value")

    state = fields.Selection(string="State", selection=[('draft', 'Draft'), ('confirm', 'Confirm'), ('paid', 'Paid'), ],
                             default="draft", required=False,track_visibility='always', )

    debit_account_id = fields.Many2one('account.account', 'Debit Account',track_visibility='always',readonly=True, states={'draft': [('readonly', False)]},
                                       default=lambda self: self.env['res.config.settings'].sudo().browse(
                                           self.env['res.config.settings'].sudo().search([])[-1].id).req_leave_acc_debit_id.id if self.env['res.config.settings'].sudo().search([]) else "")
    credit_account_id = fields.Many2one('account.account', 'Credit Account',track_visibility='always',readonly=True, states={'draft': [('readonly', False)]},
                                        default=lambda self: self.env['res.config.settings'].sudo().browse(self.env['res.config.settings'].sudo().search([])[-1].id).req_leave_acc_credit_id.id if self.env['res.config.settings'].sudo().search([]) else "")
    journal_id = fields.Many2one('account.journal', 'Journal',track_visibility='always',readonly=True, states={'draft': [('readonly', False)]},
                                 default=lambda self: self.env['res.config.settings'].sudo().browse(
                                     self.env['res.config.settings'].sudo().search([])[-1].id).req_leave_journal_id.id if
                                 self.env['res.config.settings'].sudo().search([]) else "")

    pay_journal_id = fields.Many2one('account.journal', 'Payment Journal', readonly=True,
                                     states={'confirm': [('readonly', False)]},
                                     domain=[('type', 'in', ('bank', 'cash'))])

    company_id = fields.Many2one('res.company',  readonly=True, default=lambda self: self.env.company)
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
        price = self.total_allowance_value
        if not price:
            raise exceptions.ValidationError("Can't Conform with 0.0 Amount")

        vals = []

        ref = 'Leave Request# ' + self.name
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

        if not self.pay_journal_id.default_account_id:
            raise exceptions.ValidationError("Payment Journal Account Can't Be Null")

        vals = []
        price = self.total_allowance_value
        if not price:
            raise exceptions.ValidationError("Can't Conform with 0.0 Amount")
        ref = 'Leave Request# ' + self.name
        if price:
            vals.append((0, 0, {'name': ref,
                                'partner_id': partner.id,
                                'account_id': self.pay_journal_id.default_account_id.id,
                                'debit': 0.0,
                                'credit': price}))
            vals.append((0, 0, {'name': ref,
                                'partner_id': partner.id,
                                'account_id': self.debit_account_id.id,
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
        values['name'] = self.env['ir.sequence'].next_by_code('leave.order') or _('New')
        return super(leave_request, self).create(values)

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

    @api.depends('basic_salary','employee_id','number_of_days_due')
    def compute_due_days_value(self):
        for rec in self:
            rec.value_of_days_due = (rec.number_of_days_due/30) * rec.basic_salary

    @api.depends('employee_id', 'request_date')
    def cal_period_of_leave_due(self):
        for rec in self:
            days_num = ""

            if rec.employee_id and rec.employee_id.return_date_lst_lev and rec.request_date:
                start_date = rec.employee_id.return_date_lst_lev
                d1 = fields.Datetime.from_string(rec.request_date)
                d2 = fields.Datetime.from_string(start_date)
                delta = d1 - d2
                days = delta.days + 1
                days_num = str(days) + ' يوم '
            rec.period_of_leave_due = days_num


    @api.depends('employee_id','value_of_days_due','travel_ticket_value')
    def compute_allowance_value(self):
        for rec in self:
            rec.total_allowance_value = rec.value_of_days_due + rec.travel_ticket_value



