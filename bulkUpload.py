'''
    This function process for member creation from bulk csv upload and creates user login in cognito.
'''

import json
import requests
from datetime import datetime
from pytz import timezone
import concurrent.futures
from inspect import cleandoc
import mysql.connector

URL = 'https://cognitodev.shikhartech.com/cognito-user/create'
CHUNK_SIZE = 50


def get_connection():
    return mysql.connector.connect(
        host="localhost",         # Replace with your DB host
        user="root",         # Replace with your DB username
        password="Alina123@",     # Replace with your DB password
        database="vox-sneaker"          # Replace with your DB name
    )
    
def execute_query(cnx, sql, fetch=0):
    cursor = cnx.cursor(dictionary=True)
    cursor.execute(sql)

    if fetch == 1:
        result = cursor.fetchone()
    else:
        result = cursor.fetchall()

    cursor.close()
    return {} if fetch == 1 and result is None else result


def list_to_tuple(list):
    # Convert list to SQL-compatible tuple
    return f"('{list[0]}')" if (len(list) < 2) else f'{tuple(list)}'

def getCustomer(cnx, customerId):

    sql = f'''SELECT (SELECT token FROM tokens WHERE customerId = customers.id AND type = '0' LIMIT 1) AS token, isCognitoEnabled,
                (SELECT id FROM member_groups WHERE customerId = customers.id AND isDefault = '1' LIMIT 1) AS defaultMemberGroupId
                from customers
                WHERE id = {customerId}
                AND `status` = '1'
        '''

    return execute_query(cnx, sql, fetch=1)


def chunk(data, size):
    for i in range(0, len(data), size):
        yield data[i:i + size]


class Cognito:
    """
    Cognito class handles the synchronization of member data with a Cognito API.
    """

    def __init__(self, cnx, data):
        # Assign read/write DB connections
        self.cnx = cnx

        # Extract necessary info from data payload
        self.data = data
        self.customerId = data.get('customerId')
        self.memberIds = data.get("memberIds")

        # Will be populated with auth token headers after customer lookup
        self.headers = None

    def getMembers(self):
        """
        Retrieves member details from the database that match the given member IDs and customer ID.
        """
        sql = f'''
            SELECT email, badgeId, id as memberId, name, 'true' AS email_verified
            FROM members
            WHERE id IN {list_to_tuple(self.memberIds)} AND customerId = {self.customerId}
        '''
        return execute_query(self.cnx, sql)

    def post(self, payload):
        """
        Sends a POST request to the external Cognito API with member data..
        """
        try:
            response = requests.post(URL, json=payload, headers=self.headers, timeout=6)
            return response.text
        except requests.exceptions.HTTPError as e:
            return f'''Failed to send member data to Cognito API for member ID {payload.get('memberId')}:{e}'''

    def process(self):
        """
        Orchestrates the full sync process:
        - Authenticates the customer to retrieve their token.
        - Fetches the member records from the database.
        - Sends each member's data to the Cognito API in parallel using a thread pool.
        """
        # Lookup customer info and validate token availability
        customer = getCustomer(self.cnx, self.customerId)
        if not customer:
            return {'returnType': 'error', 'message': 'Customer not found for cognito enabled feature.'}

        # Set Authorization header using customer's token
        self.headers = {
            'Authorization': f"Bearer {customer.get('token')}"
        }

        # Retrieve member records from DB
        members = self.getMembers()
        if not members:
            return {'returnType': 'error', 'message': 'Members not found to be processed.'}

        # Break into chunks
        for chunkedMember in chunk(members, CHUNK_SIZE):
            # Use a thread pool to make concurrent POST requests
            with concurrent.futures.ThreadPoolExecutor() as executor:
                results = list(executor.map(self.post, chunkedMember))

                # Print only first 100 characters of each response for inspection/debugging
                for res in results:
                    print(res[:200])

        return {"returnType": "success", "message": "Members synced successfully."}


class Member:
    """
    The Member class handles operations related to importing temporary members
    from a `temp_members` into the main `members` table, checking
    for duplicates, and syncing valid new members with a Cognito-based system.
    """

    def __init__(self, cnx, wcnx, data):
        self.cnx = cnx
        self.wcnx = wcnx
        self.customerId = data.get("customerId")
        self.tempId = data.get("tempId")
        self.logId = data.get("logId")

    def getTempMembers(self):
        """
        Fetch the temporary member record from `temp_members` table using provided IDs.
        Only retrieves unprocessed entries (`flag = '0'`).
        """
        sql = f'''SELECT * FROM `temp_members`
            WHERE `id` = {self.tempId}
            AND `customerId` = {self.customerId}
            AND `memberBulkUploadId` = {self.logId}
            AND `flag` = '0'
        '''
        return execute_query(self.cnx, sql, fetch=1)

    def updateTempMembersFlag(self, flag):
        """
        Update the `flag` value in `temp_members` table to mark a record as processed or failed.
        """
        sql = f"UPDATE temp_members SET flag = '{flag}' WHERE id = {self.tempId}"
        execute_query(self.wcnx, sql)
        self.wcnx.commit()

    def getMembers(self, badgeIds, select="JSON_ARRAYAGG(badgeId) AS badgeIds"):
        """
        Fetch existing members from the `members` table who match the given badgeIds.
        Default return is a JSON array of badgeIds.
        """
        sql = f"SELECT {select} FROM `members` WHERE `badgeId` IN {list_to_tuple(badgeIds)} AND customerId = {self.customerId}"
        return execute_query(self.cnx, sql, 1)

    def insertMembers(self, inserts, userId):
        """
        Bulk insert new members into the `members` table using provided data and user ID.
        """
        time_now = datetime.now(timezone('America/Denver'))
        sql = cleandoc(f'''
            INSERT INTO `members` (name, badgeId, email, created_at, createdBy, updatedBy, customerId, updated_at)
            VALUES
                (%(name)s, %(badgeId)s, %(email)s, '{time_now}', {userId}, {userId}, {self.customerId}, '{time_now}')
        ''')

        with self.wcnx.cursor(dictionary=True) as cursor:
            cursor.executemany(sql, inserts)
        self.wcnx.commit()

    def updateTempMember(self, data):
        '''Update the `memberDetails` field in `temp_members` table with the remarked data.'''
        sql = f"UPDATE temp_members SET memberDetails = '{json.dumps(data)}' WHERE id = {self.tempId}"

        execute_query(self.wcnx, sql)
        self.wcnx.commit()

    def prepareNewMembers(self, rawMembers, existingMembers):
        '''
        Prepare new members for insertion into the `members` table.
        Checks duplicate, empty, and existing data.
        '''
        collectedBadgeIds = []
        tempMemberUpdates = []
        newMembers = []
        for rawMember in rawMembers:
            alreadyExist = True if rawMember.get("badgeId") in existingMembers else False # already exists in db
            isDuplicate = True if rawMember.get('badgeId') in collectedBadgeIds else False # duplicate data in csv
            isEmpty = True if rawMember.get('name') == '' or rawMember.get('email') == '' or rawMember.get('badgeId') == '' else False # empty data

            # update remarks
            rawMember['remarks'] = 'Insufficient Data' if isEmpty else ('Member Already Exists' if alreadyExist else ('Duplicate Inputs.' if isDuplicate else 'Created'))
            tempMemberUpdates.append(rawMember)

            # if not already exist and not duplicate and not empty, add to newMembers
            if not alreadyExist and not isDuplicate and not isEmpty:
                newMembers.append(rawMember)

            # collect badgeIds to check for duplicates
            collectedBadgeIds.append(rawMember.get('badgeId'))

        updatedTempMember = {"members": tempMemberUpdates,}

        # update temp_members with remarks for each member
        self.updateTempMember(updatedTempMember)

        return newMembers

    def insertMemberGroups(self, memberIds, groupId):
        sql = f'''INSERT INTO members_member_groups (memberId, memberGroupId) VALUES (%s, {groupId})'''

        memberIds = json.loads(memberIds)  # This gives you a list of integers
        values = [(memberId,) for memberId in memberIds]  # Make each a 1-tuple
        with self.wcnx.cursor() as cursor:
            cursor.executemany(sql, values)
        self.wcnx.commit()


    def process(self):
        """
        Main entry point to process a batch of members:
        """
        # Fetch customer info to validate token availability
        customer = getCustomer(self.cnx, self.customerId)     
        if not customer:
            return {'returnType': 'error', 'message': 'Customer not.'}
            
        if (customer.get('isCognitoEnabled') == '1' and not customer.get('token')):
            return {'returnType': 'error', 'message': 'Customer\'s cognito token not found.'}

        # Fetch the temporary member entry
        tempMemberDetail = self.getTempMembers()
        if not tempMemberDetail:
            return {'returnType': 'error', 'message': 'Temp members not found to be processed.'}

        self.updateTempMembersFlag('1')

        # Retrieve user ID from the record (used for insert tracking)
        userId = tempMemberDetail.get("createdBy")

        # # Load the actual member data (stored as JSON in DB)
        tempMemberDetail = json.loads(tempMemberDetail.get('memberDetails', '{}'))
        memberData = tempMemberDetail.get('members')

        # # Collect badge IDs from submitted members
        badgeIds = [element.get('badgeId') for element in memberData]

        # # Query DB to find existing members with those badge IDs
        existingMembers = self.getMembers(badgeIds)

        existingBadgeIds = [] if existingMembers.get('badgeIds') is None else json.loads(existingMembers.get("badgeIds", "[]"))

        # # Filter out members that already exist
        # newMembers = [person for person in memberData if person['badgeId'] not in existingBadgeIds]
        newMembers = self.prepareNewMembers(memberData, existingBadgeIds)
        if len(newMembers) > 0:
            self.insertMembers(newMembers, userId)

            self.cnx.close()
            self.cnx = get_connection()
            newMemberBadgeIds = [item['badgeId'] for item in newMembers]
            
            newMembers = self.getMembers(newMemberBadgeIds, select="JSON_ARRAYAGG(id) AS ids")
            newMemberIds = newMembers.get('ids')
            
            print(customer.get("isCognitoEnabled"))

            if newMemberIds:
                if customer.get("isCognitoEnabled") == '1':
                    # Build payload and trigger Cognito sync for new members
                    payload = {'memberIds': json.loads(newMemberIds), 'customerId': self.customerId}    
                    print("cognito")
                    Cognito(self.cnx, payload).process()

                defaultMemberGroup = customer.get('defaultMemberGroupId')

                if defaultMemberGroup:
                    self.insertMemberGroups(newMemberIds, defaultMemberGroup)

      #  self.updateTempMembersFlag('2')

        return {'returnType': 'success', 'message': 'Members processed successfully.'}

def lambda_handler(event, context):
    body = json.loads(event['Records'][0]['body'])
    requestType = body.get('type')
    cnx = get_connection()
    wcnx = get_connection()

    try:
        if requestType == "bulkCsvMember":
            process = Member(cnx, wcnx, data).process()
        elif requestType == "createCognitoUser":
            process = Cognito(cnx, body).process()
        print(process)
    except:
        raise
    finally:
        cnx.close()
        wcnx.close()


data = {
    "customerId": 1,
    "tempId": 1,
    "logId": 1,
    "type":"bulkCsvMember"
}

# data = {
#     "customerId" : 15,
#     "memberIds": [8594, 8595, 8596, 8597, 8598, 8599, 8600, 8601, 8602, 8603, 8604, 8605],
#     "type": "createCognitoUser"
# }

event = {
    'Records': [{
        "body": json.dumps(data)
    }]
}
lambda_handler(event, 0)
