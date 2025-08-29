import json
import requests
from db_utils import get_connection, execute_query
from os import getenv
import smtplib,ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

ENDPOINT = getenv('API_ENDPOINT', 'https://api.voxships.com')


def chunked(lst, size=250):
    for i in range(0, len(lst), size):
        yield lst[i:i + size]

def list_to_tuple(lst):
    if not lst:
        return "()"
    if len(lst) == 1:
        return f"({lst[0]})"
    return tuple(lst)

class DuplicateOrder:
    def __init__(self, cnx, wcnx):
        self.cnx = cnx
        self.wcnx = wcnx
        self.sender_email = "acharyakeshab2057@gmail.com"
        self.sender_password = "decixvftuizhzlmp"
        self.recipients = ["maxrai788@gmail.com", "keshav.a@shikhartech.com"]

    def get_duplicate_sales(self):
        sql = """
            SELECT inventoryOwnerId, customerId, JSON_ARRAYAGG(id) AS sale_ids
            FROM sales
            WHERE flag = 2
            AND apiComment = 'Duplicate Order.'
            GROUP BY inventoryOwnerId, customerId
        """
        return execute_query(self.cnx, sql)

    def getApiToken(self, inventoryOwnerId, customerId):
        sql = f"""
            SELECT apiToken FROM inventory_owners
            WHERE id = {inventoryOwnerId} AND customerId = {customerId}
            LIMIT 1
        """
        result = execute_query(self.wcnx, sql, fetch=1)
        return result.get("apiToken") if result else None

    def getOrderDetails(self, saleId, api_token):
        try:
            json_data = {"orderIds": saleId if isinstance(saleId, list) else [saleId]}
            
            resp = requests.post(
                f"{ENDPOINT}/orders/v3/orderDetails",
                json=json_data,
                headers={"apiToken": api_token}
            )
            
            if (data := resp.json()) and data["returnType"].lower() == "success":
                return data
            return {"returnType": "error", "message": data.get("message", "Unknown error")}
        except Exception as e:
            return {"returnType": "error", "message": str(e)}

    def bulkUpdateComments(self, sale_order_pairs: list):
        if not sale_order_pairs:
            return
        case_sql = "UPDATE sales SET apiComment = CASE "
        ids = []

        for sale_id, comment in sale_order_pairs:
            case_sql += f"WHEN id = {sale_id} THEN '{comment}' "
            ids.append(sale_id)

        case_sql += f"END WHERE id IN {list_to_tuple(ids)}"
        execute_query(self.wcnx, case_sql)
        self.wcnx.commit()

    def bulkUpdateSaleFlag(self, sale_ids, flag):
        if not sale_ids:
            return
        sql = f"UPDATE sales SET flag = {flag} WHERE id IN {list_to_tuple(sale_ids)}"
        execute_query(self.wcnx, sql)
        self.wcnx.commit()
        
        
    def connect_to_smtp_server(self):
        try:
            context = ssl.create_default_context()

            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls(context=context)
            server.login(self.sender_email, self.sender_password)
            return server
        except Exception as e:
            print("Error connecting to SMTP server:", e)
            return None

    def send_email_with_data(self, data):
        try:
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = ", ".join(self.recipients)
            msg['Subject'] = "Duplicate Orders JSON Data"

            # Email body
            body = "Please find attached the duplicate orders JSON data."
            msg.attach(MIMEText(body, 'plain'))

            # Convert the data list to JSON string
            json_content = json.dumps(data, indent=4)

            # Create MIMEBase attachment from string (in-memory)
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(json_content.encode('utf-8'))
            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                'attachment; filename="duplicate_orders.json"'
            )
            msg.attach(part)

            server = self.connect_to_smtp_server()
            if server:
                text = msg.as_string()
                server.sendmail(self.sender_email, self.recipients, text)
                server.quit()
                return True
            else:
                return False

        except Exception as e:
            print("Error sending email:", e)
            return False


    def process(self):
        if not (groups := self.get_duplicate_sales()):
            return "No duplicate sales found."
        
        data = {}
        
        for group in groups:
            inv_owner, cust_id = group["inventoryOwnerId"], group["customerId"]
            sale_ids = json.loads(group["sale_ids"])  

            apiToken = self.getApiToken(inv_owner, cust_id)
            if not apiToken:
                continue

            self.bulkUpdateSaleFlag(sale_ids, 3)
             
            for chunk in chunked(sale_ids, 250):
                sale_ids_set = set(chunk)
                warehouseOrders = self.getOrderDetails(chunk, apiToken)
                
                data = warehouseOrders.copy()

                if warehouseOrders["returnType"] == "error":
                    self.bulkUpdateSaleFlag(chunk, 2)
                    continue

                orders_map = {o["id"]: o for o in warehouseOrders["result"]["orders"]}
                order_ids_set = set(orders_map.keys())

                success_ids = list(sale_ids_set & order_ids_set)
                fail_ids = list(sale_ids_set - order_ids_set)

                sale_order_pairs = [(sid, orders_map[sid]["id"]) for sid in success_ids]

                self.bulkUpdateSaleFlag(success_ids, 1)
                self.bulkUpdateSaleFlag(fail_ids, 2)
                self.bulkUpdateComments(sale_order_pairs)
                
        email_sent = self.send_email_with_data(data)
        
        if email_sent:
            print("Email sent successfully with all JSON data.")
        else:
            print("Failed to send email.")
                            
        return "Sale sync process completed."


def lambda_handler():
    cnx, wcnx = get_connection(), get_connection()
    try:
        print(DuplicateOrder(cnx, wcnx).process())
    finally:
        cnx.close()
        wcnx.close()


lambda_handler()
