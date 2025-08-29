import requests
import mysql.connector
from os import getenv

ENDPOINT = getenv('API_ENDPOINT', 'https://api.voxships.com')


def get_connection(writer=False):
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="Alina123@",  # replace with your actual DB password
        database="vox-sneaker"
    )


def execute_query(cnx, sql, fetch=0):
    cursor = cnx.cursor(dictionary=True)
    cursor.execute(sql)

    if fetch == 1:
        result = cursor.fetchone()
    else:
        result = cursor.fetchall()

    cursor.close()
    return {} if fetch == 1 and result is None else (result if result else [])


class ProcessOrder:
    def __init__(self, cnx, wcnx, data):
        self.cnx = cnx
        self.wcnx = wcnx
        self.data = data
        self.customerId = data.get("customerId")
        self.memberId = data.get("memberId")
        self.saleId = data.get("saleId")
        self.badgeId = data.get("badgeId")

    def get_sale_detail(self):
        sql = f"""SELECT * FROM `sales`
                  WHERE `id` = {self.saleId}
                  AND `customerId` = {self.customerId}
                  AND `memberId` = {self.memberId}
                  AND `badgeId` = '{self.badgeId}'"""
        return execute_query(self.cnx, sql, fetch=1)

    def updateSaleFlag(self, flag):
        sql = f"UPDATE sales SET flag = {flag} WHERE id = {self.sale.get('id')}"
        execute_query(self.wcnx, sql)
        self.wcnx.commit()

    def getApiToken(self):
        sql = f"""SELECT * FROM `inventory_owners`
                  WHERE `id` = {self.sale.get('inventoryOwnerId')}
                  AND `customerId` = {self.sale.get('customerId')}"""
        inventoryOwner = execute_query(self.wcnx, sql, fetch=1)
        if not inventoryOwner:
            return None
        return inventoryOwner.get('apiToken')

    def getLineItems(self):
        sql = f"""SELECT sku as itemSkuNumber, quantity as itemQty, name as itemName
                  FROM `purchased_items` WHERE `saleId` = {self.sale.get('id')}"""
        return execute_query(self.wcnx, sql)

    def getShippingAddress(self):
        sql = f"""SELECT firstName, lastName, '{self.sale.get('email')}' as email,
                         address1, address2, city, state, zip, country,
                         phoneNumber as phone1
                  FROM `shipping_addresses`
                  WHERE `saleId` = {self.sale.get('id')}"""
        return execute_query(self.wcnx, sql, fetch=1) or None

    def placeVoxSwagOrder(self, json_data, api_token):
        try:
            resp = requests.post(
                f'{ENDPOINT}/orders/createOrder',
                json=json_data,
                headers={'apiToken': api_token}
            )
            data = resp.json()
            if data['returnType'].lower() == 'success':
                return {
                    'returnType': 'success',
                    'message': 'Vox Swag order placed successfully.',
                    'orderId': data['result']['orderId']
                }
            return {'returnType': 'error', 'message': data['message']}
        except Exception as e:
            return {'returnType': 'error', 'message': str(e)}

    def updateWarehouseOrderId(self, apiComment):
        sql = f"UPDATE sales SET apiComment = '{apiComment}' WHERE id = {self.sale.get('id')}"
        execute_query(self.wcnx, sql)
        self.wcnx.commit()

    def process(self):
        
        sale = self.sale = self.get_sale_detail()
        if not sale:
            return {'returnType': 'error', 'message': 'Sale not found.'}
        

        createOrderStatus = (
            sale.get('status') == 0 and
            sale.get('nonVoxFulfilled') == '0' and
            sale.get('flag') == 0
        )
        if not createOrderStatus:
            return {"returnType": "error", "message": "Order has already been processed"}

        self.updateSaleFlag(3)
        

        apiToken = self.getApiToken()
        if not apiToken:
            return f"Api token not found for inventory owner id => {sale.get('inventoryOwnerId')}"

        lineItems = self.getLineItems()
        if not lineItems:
            return f'No line items found for sale id => {sale.get("id")}'

        shippingAddress = self.getShippingAddress()
        if not shippingAddress:
            return f'Shipping address not found for sale id => {sale.get("id")}'

        json_data = {
            "orderShippingAddress": shippingAddress,
            "shipMethod": sale.get("shipMethod"),
            "productItems": lineItems,
            "orderDate": sale.get("orderDate"),
            "orderNumber": sale.get("id"),
        }
        warehouseOrder = self.placeVoxSwagOrder(json_data, apiToken)
        
        if (warehouseOrder.get("returnType") == "error"):
            self.updateWarehouseOrderId(warehouseOrder.get("message"))
            self.updateSaleFlag(2)
        else:
            self.updateWarehouseOrderId(warehouseOrder.get("orderId"))
            self.updateSaleFlag(1)

        return 'Sale sync process completed.'


def lambda_handler(event, context):
    # ✅ Directly use dict instead of JSON load
    data = event["Records"][0]["Sns"]["Message"]

    cnx = get_connection()
    wcnx = get_connection()

    try:
        processOrder = ProcessOrder(cnx, wcnx, data).process()
        print(processOrder)
    finally:
        cnx.close()
        wcnx.close()


# event = {
#     "Records": [{
#         "Sns": {
#             "Message": {
#                 "customerId": 1,
#                 "memberId": 1,
#                 "badgeId": "maxrai788@gmail.com",
#                 "saleId": 4
#             }
#         }
#     }]
# }

# lambda_handler(event, 0)
