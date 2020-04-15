# -*- coding: utf-8 -*-
from odoo import http

# class Basic_subscription(http.Controller):
#     @http.route('/basic_subscription/basic_subscription/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/basic_subscription/basic_subscription/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('basic_subscription.listing', {
#             'root': '/basic_subscription/basic_subscription',
#             'objects': http.request.env['basic.subscription''].search([]),
#         })

#     @http.route('/basic_subscription/basic_subscription/objects/<model("basic.subscription'"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('basic_subscription.object', {
#             'object': obj
#         })