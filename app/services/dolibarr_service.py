# services/dolibarr_service.py
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from typing import List, Optional
from models.dolibarr_models import (
    LlxProduct, LlxProductStock, LlxEntrepot, 
    LlxCommande, LlxCommandeDet, LlxStockMouvement
)
from datetime import datetime, timedelta

class DolibarrService:
    def __init__(self, db: Session):
        self.db = db
    
    # 🔍 CONSULTAS DE PRODUCTOS
    def get_product_by_ref(self, ref: str) -> Optional[LlxProduct]:
        """Buscar producto por referencia"""
        return self.db.query(LlxProduct).filter(
            LlxProduct.ref == ref
        ).first()
    
    def get_product_by_barcode(self, barcode: str) -> Optional[LlxProduct]:
        """Buscar producto por código de barras"""
        return self.db.query(LlxProduct).filter(
            LlxProduct.barcode == barcode
        ).first()
    
    def search_products(self, search_term: str, limit: int = 50) -> List[LlxProduct]:
        """Buscar productos por término"""
        return self.db.query(LlxProduct).filter(
            or_(
                LlxProduct.ref.ilike(f"%{search_term}%"),
                LlxProduct.label.ilike(f"%{search_term}%"),
                LlxProduct.description.ilike(f"%{search_term}%"),
                LlxProduct.barcode.ilike(f"%{search_term}%")
            )
        ).limit(limit).all()
    
    # 📦 CONSULTAS DE STOCK
    def get_product_stock(self, product_id: int, warehouse_id: Optional[int] = None) -> List[dict]:
        """Obtener stock de un producto por almacén"""
        query = self.db.query(
            LlxProductStock,
            LlxEntrepot.label
        ).join(
            LlxEntrepot, LlxProductStock.fk_entrepot == LlxEntrepot.rowid
        ).filter(
            LlxProductStock.fk_product == product_id
        )
        
        if warehouse_id:
            query = query.filter(LlxProductStock.fk_entrepot == warehouse_id)
        
        results = query.all()
        
        return [
            {
                "warehouse_id": stock.fk_entrepot,
                "warehouse_label": label,
                "stock": stock.reel,
                "product_id": stock.fk_product,
                "last_update": stock.tms
            }
            for stock, label in results
        ]
    
    def get_total_stock(self, product_id: int) -> float:
        """Stock total en todos los almacenes"""
        result = self.db.query(
            func.sum(LlxProductStock.reel)
        ).filter(
            LlxProductStock.fk_product == product_id
        ).scalar()
        
        return result or 0.0
    
    # 📋 CONSULTAS DE ÓRDENES PENDIENTES
    def get_pending_orders(self, warehouse_id: Optional[int] = None) -> List[dict]:
        """Órdenes validadas (estado=1) listas para picking"""
        query = self.db.query(LlxCommande).filter(
            LlxCommande.fk_statut == 1  # Validada
        )
        
        if warehouse_id:
            query = query.filter(LlxCommande.fk_entrepot == warehouse_id)
        
        orders = query.order_by(LlxCommande.date_commande.asc()).all()
        
        return [
            {
                "id": order.rowid,
                "ref": order.ref,
                "client_ref": order.ref_client,
                "date": order.date_commande,
                "warehouse_id": order.fk_entrepot,
                "total": float(order.total_ttc) if order.total_ttc else 0.0
            }
            for order in orders
        ]
    
    def get_order_lines(self, order_id: int) -> List[dict]:
        """Líneas de una orden específica"""
        lines = self.db.query(LlxCommandeDet).filter(
            LlxCommandeDet.fk_commande == order_id
        ).all()
        
        return [
            {
                "id": line.rowid,
                "product_id": line.fk_product,
                "description": line.description,
                "quantity_ordered": line.qty,
                "quantity_shipped": line.qty_shipped,
                "quantity_pending": line.qty - line.qty_shipped,
                "unit_price": float(line.subprice) if line.subprice else 0.0,
                "warehouse_id": line.fk_entrepot
            }
            for line in lines if line.qty > line.qty_shipped  # Solo líneas pendientes
        ]
    
    # 📊 CONSULTAS DE MOVIMIENTOS
    def get_recent_movements(self, days: int = 7, limit: int = 100) -> List[dict]:
        """Movimientos recientes de stock"""
        since_date = datetime.utcnow() - timedelta(days=days)
        
        movements = self.db.query(LlxStockMouvement).filter(
            LlxStockMouvement.datem >= since_date
        ).order_by(
            LlxStockMouvement.datem.desc()
        ).limit(limit).all()
        
        return [
            {
                "id": mov.rowid,
                "date": mov.datem,
                "product_id": mov.fk_product,
                "warehouse_id": mov.fk_entrepot,
                "quantity": mov.value,
                "type": "IN" if mov.value > 0 else "OUT",
                "label": mov.label,
                "user_id": mov.fk_user_author
            }
            for mov in movements
        ]
    
    # 🔄 CREACIÓN DE MOVIMIENTOS (CAUTELA: solo en MVP avanzado)
    def create_stock_movement(self, product_id: int, warehouse_id: int, 
                            quantity: float, label: str, user_id: int = 1) -> bool:
        """Crear movimiento de stock en Dolibarr (PELIGROSO en producción)"""
        try:
            # ⚠️ ADVERTENCIA: Esto modifica directamente Dolibarr
            # Solo para MVP de prueba, en producción usar API REST
            movement = LlxStockMouvement(
                fk_product=product_id,
                fk_entrepot=warehouse_id,
                value=quantity,
                label=label,
                fk_user_author=user_id,
                datem=datetime.utcnow(),
                tms=datetime.utcnow()
            )
            
            self.db.add(movement)
            
            # Actualizar stock en tabla llx_product_stock
            stock = self.db.query(LlxProductStock).filter(
                and_(
                    LlxProductStock.fk_product == product_id,
                    LlxProductStock.fk_entrepot == warehouse_id
                )
            ).first()
            
            if stock:
                stock.reel = stock.reel + quantity
                stock.tms = datetime.utcnow()
            else:
                # Si no existe registro, crear uno
                new_stock = LlxProductStock(
                    fk_product=product_id,
                    fk_entrepot=warehouse_id,
                    reel=quantity,
                    tms=datetime.utcnow()
                )
                self.db.add(new_stock)
            
            self.db.commit()
            return True
            
        except Exception as e:
            self.db.rollback()
            print(f"Error creando movimiento: {e}")
            return False