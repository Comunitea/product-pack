# Copyright 2021 Tecnativa - David Vidal
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import models, api


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    @api.multi
    def _prepare_procurement_values(self, group_id=False):
        values = super()._prepare_procurement_values(group_id=group_id)
        if self.pack_parent_line_id:
            values["sale_line_id"] = self.pack_parent_line_id.id
        return values

    @api.multi
    def _get_delivered_qty(self):
        res = super()._get_delivered_qty()
        qty = 0
        self.ensure_one()
        if self.pack_child_line_ids:
            # Calculamos la cantidad de producto en base a componentes.
            # En caso de incongruencia de cantidades P.E.: 1pack = 5A + 4B
            # cantidades entregadas 8A y 6B. Se establece la cantidad
            # minima de pack.
            moves = self.move_ids.filtered(
                lambda r: r.state == 'done' and not r.scrapped)
            quantities = {x.product_id.id: x.quantity for x in self.product_id.pack_line_ids}
            delivered_qties = {}
            returned_qties = {}
            for move in moves:
                pack_qty = move.product_uom_qty
                if move.location_dest_id.usage == "customer":
                    if not move.origin_returned_move_id or \
                            (move.origin_returned_move_id and move.to_refund):
                        if move.product_id.id not in delivered_qties:
                            delivered_qties[move.product_id.id] = 0.0
                        delivered_qties[move.product_id.id] += pack_qty
                elif move.location_dest_id.usage != "customer" and \
                        move.to_refund:
                    if move.product_id.id not in returned_qties:
                        returned_qties[move.product_id.id] = 0.0
                    returned_qties[move.product_id.id] += pack_qty
                delivered = self._get_pack_quantity(delivered_qties, quantities)
                returned = self._get_pack_quantity(returned_qties, quantities)
                qty = delivered - returned
            res = qty
        return res

    def _get_pack_quantity(self, quantities, bom_quantities):
        if not quantities:
            return 0.0
        pack_qty = self.product_uom_qty
        for product_id in quantities.keys():
            qty = quantities[product_id] / bom_quantities[product_id]
            if qty < pack_qty:
                pack_qty = qty
        return pack_qty
