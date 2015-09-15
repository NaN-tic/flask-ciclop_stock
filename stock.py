from flask import Blueprint, render_template, current_app, abort, g, url_for, \
    session, request, jsonify
from ciclop.tryton import tryton
from ciclop.helpers import login_required
from ciclop.api import api
from flask.ext.babel import gettext as _
from trytond.transaction import Transaction
import datetime

stock = Blueprint('stock', __name__, template_folder='templates')

ShipmentOut = tryton.pool.get('stock.shipment.out')
ShipmentOutReturn = tryton.pool.get('stock.shipment.out.return')
ShipmentIn = tryton.pool.get('stock.shipment.in')
ShipmentInReturn = tryton.pool.get('stock.shipment.in.return')
Product = tryton.pool.get('product.product')
Date = tryton.pool.get('ir.date')

OUT_FIELDS =['code', 'rec_name', 'customer.rec_name', 'delivery_address.full_address', 'state']
IN_FIELDS =['code', 'rec_name', 'supplier.rec_name', 'contact_address.full_address', 'state']
LIMIT = current_app.config.get('TRYTON_STOCK_LIMIT', 100)

@api.route("/stock/in/", endpoint="api-shipments-in")
@login_required
@tryton.transaction()
def api_shipments_in():
    '''API Suppliers Shipments'''
    # limit
    limit = request.args.get('limit') or session.get('stock_limit')
    if limit:
        try:
            limit = int(request.args.get('limit'))
        except:
            limit = LIMIT
    else:
        limit = LIMIT

    # search
    q = request.args.get('q') or session.get('stock_q')
    if q:
        domain = ['OR',
            ('rec_name', 'ilike', q),
            ('supplier', 'ilike', q),
            ('contact_address', 'ilike', q),
            ('state', 'ilike', q),
            ]
    else:
        domain = []
    state= request.args.get('state') or session.get('stock_in_state')
    if state:
        domain.append(('state', '=', state))

    total = ShipmentIn.search_count(domain)
    shipments = ShipmentIn.search_read(domain, limit=limit, fields_names=IN_FIELDS)
    return jsonify(results=shipments, total=total)

@stock.route("/in/", endpoint="shipments-in")
@login_required
@tryton.transaction()
def shipments_in(lang):
    '''Supplier Shipments'''

    if request.args.get('limit'):
        session['stock_limit'] = request.args.get('limit')
    if request.args.get('state'):
        session['stock_in_state'] = request.args.get('state')
    else:
        if session.get('stock_in_state'):
            session.pop('stock_in_state', None)
    if request.args.get('q'):
        session['stock_q'] = request.args.get('q')
    else:
        if session.get('stock_q'):
            session.pop('stock_q', None)

    #breadcumbs
    breadcrumbs = [{
        'slug': url_for('.shipments-in', lang=g.language),
        'name': _('Supplier Shipments'),
        }]

    return render_template('shipments-in.html',
            breadcrumbs=breadcrumbs,
            )

@stock.route("/in/<int:id>", endpoint="shipment-in")
@login_required
@tryton.transaction()
def shipment_in(lang, id):
    '''Supplier Shipment Detail'''
    shipments = ShipmentIn.search([
        ('id', '=', id),
        ], limit=1)
    if not shipments:
        abort(404)

    shipment, = ShipmentIn.browse(shipments)

    #breadcumbs
    breadcrumbs = [{
        'slug': url_for('.shipments-in', lang=g.language),
        'name': _('Supplier Shipments'),
        }, {
        'slug': url_for('.shipment-in', lang=g.language, id=shipment.id),
        'name': shipment.code or _('Not reference'),
        }]

    return render_template('shipment-in.html',
            breadcrumbs=breadcrumbs,
            shipment=shipment,
            )

@api.route("/stock/out/", endpoint="api-shipments-out")
@login_required
@tryton.transaction()
def api_shipments_out():
    '''API Customer Shipments'''
    # limit
    limit = request.args.get('limit') or session.get('stock_limit')
    if limit:
        try:
            limit = int(request.args.get('limit'))
        except:
            limit = LIMIT
    else:
        limit = LIMIT

    # search
    q = request.args.get('q') or session.get('stock_q')
    if q:
        domain = ['OR',
            ('rec_name', 'ilike', q),
            ('customer', 'ilike', q),
            ('delivery_address', 'ilike', q),
            ('state', 'ilike', q),
            ]
    else:
        domain = []
    state= request.args.get('state') or session.get('stock_state')
    if state:
        domain.append(('state', '=', state))

    total = ShipmentOut.search_count(domain)
    shipments = ShipmentOut.search_read(domain, limit=limit, fields_names=OUT_FIELDS)
    return jsonify(results=shipments, total=total)

@stock.route("/out/", endpoint="shipments-out")
@login_required
@tryton.transaction()
def shipments_out(lang):
    '''Customer Shipments'''

    if request.args.get('limit'):
        session['stock_limit'] = request.args.get('limit')
    if request.args.get('state'):
        session['stock_out_state'] = request.args.get('state')
    else:
        if session.get('stock_out_state'):
            session.pop('stock_out_state', None)
    if request.args.get('q'):
        session['stock_q'] = request.args.get('q')
    else:
        if session.get('stock_q'):
            session.pop('stock_q', None)

    #breadcumbs
    breadcrumbs = [{
        'slug': url_for('.shipments-out', lang=g.language),
        'name': _('Customer Shipments'),
        }]

    return render_template('shipments-out.html',
            breadcrumbs=breadcrumbs,
            )

@stock.route("/out/<int:id>", endpoint="shipment-out")
@login_required
@tryton.transaction()
def shipment_out(lang, id):
    '''Customer Shipment Detail'''
    shipments = ShipmentOut.search([
        ('id', '=', id),
        ], limit=1)
    if not shipments:
        abort(404)

    shipment, = ShipmentOut.browse(shipments)

    #breadcumbs
    breadcrumbs = [{
        'slug': url_for('.shipments-out', lang=g.language),
        'name': _('Customer Shipments'),
        }, {
        'slug': url_for('.shipment-out', lang=g.language, id=shipment.id),
        'name': shipment.code or _('Not reference'),
        }]

    return render_template('shipment-out.html',
            breadcrumbs=breadcrumbs,
            shipment=shipment,
            )

@stock.route("/product/", endpoint="product")
@login_required
@tryton.transaction()
def product(lang):
    '''Product'''
    product = None
    qty_by_location = {}
    forecast_by_location = {}
    q = request.args.get('q')

    if q:
        today = Date.today()

        products = Product.search([
            ('rec_name', '=', q),
            ], limit=1)
        if products:
            product, = products

            locations_ids = [l.location.id for l in product.locations]
            products = [product.id]

            context = {
                'stock_date_start': today,
                'product': product.id,
                }
            context['forecast'] = False
            context['stock_date_end'] = today
            with Transaction().set_context(**context):
                qty_by_location = Product.products_by_location(
                    locations_ids, products)

            context['forecast'] = True
            context['stock_date_end'] = datetime.date.max
            with Transaction().set_context(**context):
                forecast_by_location = Product.products_by_location(
                    locations_ids, products)
            print qty_by_location
            print forecast_by_location

    #breadcumbs
    breadcrumbs = [{
        'slug': url_for('.product', lang=g.language),
        'name': _('Product'),
        }]

    return render_template('stock-product.html',
            breadcrumbs=breadcrumbs,
            product=product,
            qty_by_location=qty_by_location,
            forecast_by_location=forecast_by_location,
            q=q,
            )
