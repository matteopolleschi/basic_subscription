# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.addons import decimal_precision as dp

class Basic_subscription(models.Model):
    _name = 'basic.subscription'
    _description = "Subscription"
    _inherit = ['mail.thread', 'mail.activity.mixin']


    def _get_default_pricelist(self):
        return self.env['product.pricelist'].search([('currency_id', '=', self.env.user.company_id.currency_id.id)], limit=1).id
    
    name = fields.Char(required=True, track_visibility="always", default="New")
    description = fields.Text()
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account')
    code = fields.Char(string="Reference", required=True, track_visibility="onchange", index=True, copy=False)
    stage_id = fields.Many2one('basic.subscription.stage', string='Stage', index=True, default=lambda s: s._get_default_stage_id(), group_expand='_read_group_stage_ids', track_visibility='onchange')
    company_id = fields.Many2one('res.company', string="Company", default=lambda s: s.env['res.company']._company_default_get(), required=True)
    partner_id = fields.Many2one('res.partner', string='Customer', required=True, auto_join=True)
    date_start = fields.Date(string='Start Date', default=fields.Date.today)
    date_end = fields.Date(string='End Date', track_visibility='onchange', help="If set in advance, the subscription will be set to pending 1 month before the date and will be closed on the date set in this field.")
    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist', default=_get_default_pricelist, required=True)
    currency_id = fields.Many2one('res.currency', related='pricelist_id.currency_id', string='Currency', readonly=True)  
    recurring_invoice_line_ids = fields.One2many('basic.subscription.line', 'analytic_account_id', string='Invoice Lines', copy=True)
    recurring_rule_type = fields.Selection(string='Recurrence', help="Invoice automatically repeat at specified interval", related="template_id.recurring_rule_type", readonly=1)
    recurring_interval = fields.Integer(string='Repeat Every', help="Repeat every (Days/Week/Month/Year)", related="template_id.recurring_interval", readonly=1)
    recurring_next_date = fields.Date(string='Date of Next Invoice', default=fields.Date.today, help="The next invoice will be created on this date then the period will be extended.")
    recurring_total = fields.Float(compute='_compute_recurring_total', string="Recurring Price", store=True, track_visibility='onchange')
    recurring_monthly = fields.Float(compute='_compute_recurring_monthly', string="Monthly Recurring Revenue", store=True)
    template_id = fields.Many2one('basic.subscription.template', string='Subscription Template', required=True, track_visibility='onchange')
    payment_mode = fields.Selection(related='template_id.payment_mode', readonly=False)
    user_id = fields.Many2one('res.users', string='Salesperson', track_visibility='onchange', default=lambda self: self.env.user)
    team_id = fields.Many2one('crm.team', 'Sales Team', change_default=True, default=False)
    team_user_id = fields.Many2one('res.users', string="Team Leader", related="team_id.user_id", readonly=False)
    country_id = fields.Many2one('res.country', related='partner_id.country_id', store=True, readonly=False, compute_sudo=True)
    industry_id = fields.Many2one('res.partner.industry', related='partner_id.industry_id', store=True, readonly=False)
    recurring_amount_tax = fields.Float('Taxes', compute="_amount_all")
    recurring_amount_total = fields.Float('Total', compute="_amount_all")
    recurring_rule_boundary = fields.Selection(related="template_id.recurring_rule_boundary", readonly=False)
    token = fields.Char(string="Token")
    tag_ids = fields.Many2many('basic.subscription.tag', string='Tags')
    website_url = fields.Char('Website URL', help='The full URL to access the document through the website.')
    in_progress = fields.Boolean(related='stage_id.in_progress')
    to_renew = fields.Boolean(string='To Renew', default=False, copy=False)
    color = fields.Integer()
    
    def _get_default_stage_id(self):
        return self.env['basic.subscription.stage'].search([], order='sequence', limit=1)

    @api.model
    def _read_group_stage_ids(self, stages, domain, order):
        return stages.sudo().search([], order=order)

    def name_get(self):
        res = []
        for sub in self:
            name = '%s - %s' % (sub.code, sub.partner_id.sudo().display_name) if sub.code else sub.partner_id.display_name
            res.append((sub.id, '%s' % name))
        return res
    
    @api.model
    def create(self, vals):
        vals['code'] = (
            vals.get('code') or
            self.env.context.get('default_code') or
            self.env['ir.sequence'].with_context(force_company=vals.get('company_id')).next_by_code('basic.subscription') or
            'New'
        )
        if vals.get('name', 'New') == 'New':
            vals['name'] = vals['code']
        subscription = super(Basic_subscription, self).create(vals)
        return subscription

    def write(self, vals):
        result = super(Basic_subscription, self).write(vals)
        return result
    
    @api.depends('recurring_invoice_line_ids', 'recurring_invoice_line_ids.quantity', 'recurring_invoice_line_ids.price_subtotal')
    def _compute_recurring_total(self):
        for account in self:
            account.recurring_total = sum(line.price_subtotal for line in account.recurring_invoice_line_ids)

    @api.depends('recurring_total', 'template_id.recurring_interval', 'template_id.recurring_rule_type')
    def _compute_recurring_monthly(self):
        interval_factor = {
            'daily': 30.0,
            'weekly': 30.0 / 7.0,
            'monthly': 1.0,
            'yearly': 1.0 / 12.0,
        }
        for sub in self:
            sub.recurring_monthly = (
                sub.recurring_total * interval_factor[sub.recurring_rule_type] / sub.recurring_interval
            ) if sub.template_id else 0

    @api.depends('recurring_invoice_line_ids', 'recurring_total')
    def _amount_all(self):
        for account in self:
            val = val1 = 0.0
            cur = account.pricelist_id.sudo().currency_id
            for line in account.recurring_invoice_line_ids:
                val1 += line.price_subtotal
                val += line._amount_line_tax()
            account.recurring_amount_tax = cur.round(val)
            account.recurring_amount_total = account.recurring_amount_tax + account.recurring_total


class Basic_subscription_stage(models.Model):
    _name = 'basic.subscription.stage'
    _description = "Subscription Stage"
    _order = 'sequence, id'

    name = fields.Char(string='Stage Name', required=True)
    description = fields.Text()
    sequence = fields.Integer(default=1)
    in_progress = fields.Boolean(string='In Progress', default=True)
    fold = fields.Boolean(string='Folded in Kanban', help='This stage is folded in the kanban view when there are not records in that stage to display.')
    rating_template_id = fields.Many2one('mail.template', string='Rating Email Template', domain=[('model', '=', 'basic.subscription')])


class Basic_subscription_template(models.Model):
    _name = "basic.subscription.template"
    _description = "Subscription Template"
    _inherit = ['mail.thread']

    active = fields.Boolean(default=True)
    name = fields.Char(required=True)
    code = fields.Char()
    description = fields.Text(translate=True, string="Terms and Conditions")

    recurring_rule_type = fields.Selection([('daily', 'Day(s)'), ('weekly', 'Week(s)'), ('monthly', 'Month(s)'), ('yearly', 'Year(s)'), ],
                                           string='Recurrence', required=True,
                                           help="Invoice automatically repeat at specified interval",
                                           default='monthly', track_visibility='onchange')

    recurring_interval = fields.Integer(string="Repeat Every", help="Repeat every (Days/Week/Month/Year)", required=True, default=1, track_visibility='onchange')
    recurring_rule_boundary = fields.Selection([('unlimited', 'Forever'),('limited', 'Fixed')], string='Duration', default='unlimited')
    recurring_rule_count = fields.Integer(string="End After", default=1)
    recurring_rule_type_readonly = fields.Selection(string="Recurrence Unit", related='recurring_rule_type', readonly=True, track_visibility=False)

    payment_mode = fields.Selection([
        ('manual', 'Manual'),
        ('draft_invoice', 'Draft invoice'),
        ('validate_send', 'Invoice'),
        ('validate_send_payment', 'Invoice & try to charge'),
        ('success_payment', 'Invoice only on successful payment'),
    ], required=True, default='draft_invoice')

    color = fields.Integer()

    @api.constrains('recurring_interval')
    def _check_recurring_interval(self):
        if self.recurring_interval <= 0:
            raise ValidationError(_("The recurring interval must be positive"))

    def name_get(self):
        res = []
        for sub in self:
            name = '%s - %s' % (sub.code, sub.name) if sub.code else sub.name
            res.append((sub.id, name))
        return res


class Basic_subscription_line(models.Model):
    _name = "basic.subscription.line"
    _description = "Subscription Line"

    def _get_default_uom_id(self):
        return self.env['uom.uom'].search([], limit=1, order='id').id

    product_id = fields.Many2one('product.product', string='Product', required=True)
    analytic_account_id = fields.Many2one('basic.subscription', string='Subscription')
    name = fields.Text(string='Description', required=True)
    quantity = fields.Float(string='Quantity', help="Quantity that will be invoiced.", default=1.0)
    uom_id = fields.Many2one('uom.uom', default=_get_default_uom_id, string='Unit of Measure', required=True)

    price_unit = fields.Float(string='Unit Price', required=True, digits=dp.get_precision('Product Price'))
    discount = fields.Float(string='Discount (%)', digits=dp.get_precision('Discount'))
    price_subtotal = fields.Float(compute='_compute_price_subtotal', string='Sub Total', digits=dp.get_precision('Account'), store=True)

    @api.depends('price_unit', 'quantity', 'discount', 'analytic_account_id.pricelist_id')
    def _compute_price_subtotal(self):
        for line in self:
            price = line.env['account.tax']._fix_tax_included_price(line.price_unit, line.product_id.sudo().taxes_id, [])
            line.price_subtotal = line.quantity * price * (100.0 - line.discount) / 100.0
            if line.analytic_account_id.pricelist_id.sudo().currency_id:
                line.price_subtotal = line.analytic_account_id.pricelist_id.sudo().currency_id.round(line.price_subtotal)

    @api.onchange('product_id')
    def onchange_product_id(self):
        product = self.product_id
        partner = self.analytic_account_id.partner_id
        if partner.lang:
            product = product.with_context(lang=partner.lang)

        self.name = product.get_product_multiline_description_sale()

    @api.onchange('product_id', 'quantity')
    def onchange_product_quantity(self):
        domain = {}
        subscription = self.analytic_account_id
        company_id = subscription.company_id.id
        pricelist_id = subscription.pricelist_id.id
        context = dict(self.env.context, company_id=company_id, force_company=company_id, pricelist=pricelist_id, quantity=self.quantity)
        if not self.product_id:
            self.price_unit = 0.0
            domain['uom_id'] = []
        else:
            partner = subscription.partner_id.with_context(context)
            if partner.lang:
                context.update({'lang': partner.lang})

            product = self.product_id.with_context(context)
            self.price_unit = product.price

            if not self.uom_id:
                self.uom_id = product.uom_id.id
            if self.uom_id.id != product.uom_id.id:
                self.price_unit = product.uom_id._compute_price(self.price_unit, self.uom_id)
            domain['uom_id'] = [('category_id', '=', product.uom_id.category_id.id)]

        return {'domain': domain}

    @api.onchange('uom_id')
    def onchange_uom_id(self):
        if not self.uom_id:
            self.price_unit = 0.0
            return {'domain': {'uom_id': [('category_id', '=', self.product_id.uom_id.category_id.id)]}}
        else:
            return self.onchange_product_quantity()

    def get_template_option_line(self):
        """ Return the account.analytic.invoice.line.option which has the same product_id as
        the invoice line"""
        if not self.analytic_account_id and not self.analytic_account_id.template_id:
            return False
        template = self.analytic_account_id.template_id
        return template.sudo().subscription_template_option_ids.filtered(lambda r: r.product_id == self.product_id)

    def _amount_line_tax(self):
        self.ensure_one()
        val = 0.0
        product = self.product_id
        product_tmp = product.sudo().product_tmpl_id
        for tax in product_tmp.taxes_id.filtered(lambda t: t.company_id == self.analytic_account_id.company_id):
            fpos_obj = self.env['account.fiscal.position']
            partner = self.analytic_account_id.partner_id
            fpos_id = fpos_obj.with_context(force_company=self.analytic_account_id.company_id.id).get_fiscal_position(partner.id)
            fpos = fpos_obj.browse(fpos_id)
            if fpos:
                tax = fpos.map_tax(tax, product, partner)
            compute_vals = tax.compute_all(self.price_unit * (1 - (self.discount or 0.0) / 100.0), self.analytic_account_id.currency_id, self.quantity, product, partner)['taxes']
            if compute_vals:
                val += compute_vals[0].get('amount', 0)
        return val

    @api.model
    def create(self, values):
        if values.get('product_id') and not values.get('name'):
            line = self.new(values)
            line.onchange_product_id()
            values['name'] = line._fields['name'].convert_to_write(line['name'], line)
        return super(Basic_subscription_line, self).create(values)


class Basic_subscription_tag(models.Model):
    _name = 'basic.subscription.tag'
    _description = "Subscription Tag"

    name = fields.Char(string='Tag Name', required=True)
    color = fields.Integer()