import mysql.connector
import requests

class Database:
    def __init__(self, host, user, password, database):
        self.host = host
        self.user = user
        self.password = password
        self.database = database

    def execute_query(self, query, params=None):
        try:
            connection = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database
            )
            cursor = connection.cursor()
            cursor.execute(query, params)
            result = cursor.fetchall()
            connection.commit()
            return result
        except mysql.connector.Error as err:
            return None
        finally:
            cursor.close()
            connection.close()


class OrderProcessor:
    def __init__(self, db, api_url):
        self.db = db
        self.api_url = api_url

    def get_order(self, customer_id, member_id, badge_id, sale_id):
        query = """
        SELECT 
            Sale.*, 
            PurchasedItems.sku, 
            PurchasedItems.quantity, 
            PurchasedItems.name, 
            ShippingAddress.firstName, 
            ShippingAddress.lastName, 
            ShippingAddress.address1, 
            ShippingAddress.address2, 
            ShippingAddress.city, 
            ShippingAddress.state, 
            ShippingAddress.zip, 
            ShippingAddress.country, 
            ShippingAddress.phoneNumber 
        FROM 
            Sale
        LEFT JOIN 
            PurchasedItems ON PurchasedItems.saleId = Sale.id
        LEFT JOIN 
            ShippingAddress ON ShippingAddress.id = Sale.shippingAddressId
        WHERE 
            Sale.customerId = %s AND 
            Sale.memberId = %s AND 
            Sale.badgeId = %s AND 
            Sale.id = %s
        """
        params = (customer_id, member_id, badge_id, sale_id)
        result = self.db.execute_query(query, params)
        return result if result else None

    def get_inventory_owner_token(self, inventory_owner_id):
        query = "SELECT apiToken FROM InventoryOwner WHERE id = %s"
        params = (inventory_owner_id,)
        result = self.db.execute_query(query, params)
        return result[0]['apiToken'] if result else None

    def get_item_details(self, sale_id):
        query = """
        SELECT sku, quantity, name FROM PurchasedItems WHERE saleId = %s
        """
        return self.db.execute_query(query, (sale_id,))

    def get_shipping_address(self, shipping_address_id):
        query = """
        SELECT firstName, lastName, address1, address2, city, state, zip, country, phoneNumber
        FROM ShippingAddress WHERE id = %s
        """
        result = self.db.execute_query(query, (shipping_address_id,))
        return result[0] if result else None

    def update_order_status(self, sale_id, flag, comment):
        query = "UPDATE Sale SET flag = %s, apiComment = %s WHERE id = %s"
        params = (flag, comment, sale_id)
        self.db.execute_query(query, params)

    def process_order(self, data):
        order = self.get_order(data['customerId'], data['memberId'], data['badgeId'], data['saleId'])
        if not order:
            return {"status": "failure", "message": "Sales Data Not Found."}

        if not data.get('apiToken'):
            data['apiToken'] = self.get_inventory_owner_token(order['inventoryOwnerId'])

        if order['status'] == 0 and order['nonVoxFulfilled'] == '0':
            ItemDetails = []
            item_details = self.get_item_details(order['id'])

            for detail in item_details:  
                ItemDetails.append({
                    'itemSkuNumber': detail['sku'],
                    'itemQty': detail['quantity'],
                    'itemName': detail['name']
                })

            shipping_address = self.get_shipping_address(order['shippingAddressId'])

            order_shipping_address = {
                'firstName': shipping_address['firstName'],
                'lastName': shipping_address['lastName'],
                'email': order['email'],
                'address1': shipping_address['address1'],
                'address2': shipping_address['address2'],
                'city': shipping_address['city'],
                'state': shipping_address['state'],
                'zip': shipping_address['zip'],
                'country': shipping_address['country'],
                'phone1': shipping_address['phoneNumber'],
            }

            response_data = self.create_order_api_request(order, item_details, order_shipping_address, data['apiToken'])

            if response_data.get('returnType') == 'success':
                self.update_order_status(order['id'], 1, response_data['result']['orderId'])
            else:
                self.update_order_status(order['id'], 2, response_data['message'])

    def create_order_api_request(self, order, item_details, order_shipping_address, api_token):
        response = requests.post(
            f'{self.api_url}/orders/createOrder',
            json={
                'orderNumber': order['id'],
                'shipMethod': order['shipMethod'],
                'orderDate': order['created_at'],
                'productItems': item_details,
                'orderShippingAddress': order_shipping_address,
            },
            headers={'apiToken': api_token},
            verify=False
        )
        return response.json()


if __name__ == '__main__':
    db = Database(host='localhost', user='root', password='', database='vox')
    order_processor = OrderProcessor(db, api_url='https://api.voxships.com')
    
    data = {
        'customerId': 123,
        'memberId': 456,
        'badgeId': 789,
        'saleId': 101112,
        'apiToken': 'nothing'
    }

    order_processor.process_order(data)
