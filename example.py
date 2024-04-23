
from datetime import datetime
from stcore import pms
from pytz import timezone

# Function to execute a SQL query
OLD_STORE_ID = 131
NEW_STORE_ID = 162
TODAY_DATE = datetime.now(timezone('America/Denver')).strftime('%Y-%m-%d')


def execute_query(cnx, sql, commit=True):
    with cnx.cursor() as cursor:
        cursor.execute(sql)

        if commit:
            cnx.commit()
        else:
            return cursor.fetchall()


def chunk(data, chunk):
    for i in range(0, len(data), chunk):
        yield data[i:i + chunk]


def clone_attribute(wcnx):
    # old id is saved in list_order column
    sql = f'''
            INSERT INTO
                `attribute` (
                    `parent`, `store_id`, `name`, `status`, `flag`, `created_at`, `updated_at`, `created_by`, `updated_by`, `list_order`, `code`
                )
            SELECT
                parent,
                {NEW_STORE_ID},
                `name`,
                `status`,
                `flag`,
                '{TODAY_DATE}',
                '{TODAY_DATE}',
                `created_by`,
                `updated_by`,
                `id`,
                `code`
            FROM `attribute`
            WHERE
                `store_id` = {OLD_STORE_ID} ORDER BY parent;
'''

    execute_query(wcnx, sql)
    sql = f'''
             UPDATE attribute a1
            set
                parent = (select id from
                (
                    SELECT id
                    FROM attribute a2
                    WHERE
                        a1.parent = a2.list_order
                        AND store_id = {NEW_STORE_ID}
                    LIMIT 1
                ) as t)
            where
                store_id = {NEW_STORE_ID} AND
                parent IS NOT NULL
        '''

    execute_query(wcnx, sql)


def clone_category(wcnx):
    # old id is saved in list_order column
    sql = f'''INSERT INTO
                `category` (
                    `parent`, `store_id`, `name`, `status`, `created_by`, `created_at`, `updated_by`, `updated_at`, `list_order`, `banner_path`, `third_party_url`, `is_amazon_or_we_gift`
                )
            SELECT
                (
                    SELECT id
                    from `category`
                    WHERE
                        `list_order` = `parent`
                    LIMIT 1
                ),
                {NEW_STORE_ID},
                `name`,
                `status`,
                `created_by`,
                '{TODAY_DATE}',
                `updated_by`,
                '{TODAY_DATE}',
                `id`,
                `banner_path`,
                `third_party_url`,
                `is_amazon_or_we_gift`
            FROM `category`
            WHERE
                `store_id` = {OLD_STORE_ID};'''
    execute_query(wcnx, sql)


def clone_credit_type(wcnx):
    # old id is saved in list_order column
    sql = f'''INSERT INTO
                `credit_type` (
                    `store_id`, `is_recognition`, `name`, `recognited_id`, `description`, `credit_currency_code`, `status`, `retail_flag`, `is_primary`, `created_by`, `created_at`, `updated_by`, `updated_at`, `list_order`, `is_amazon`, `is_giftcard`, `is_cac`, `is_payroll`, `is_recognizable`, `is_shipping`
                )
            SELECT
                {NEW_STORE_ID},
                `is_recognition`,
                `name`,
                `recognited_id`,
                `description`,
                `credit_currency_code`,
                `status`,
                `retail_flag`,
                `is_primary`,
                `created_by`,
                '{TODAY_DATE}',
                `updated_by`,
                '{TODAY_DATE}',
                `id`,
                `is_amazon`,
                `is_giftcard`,
                `is_cac`,
                `is_payroll`,
                `is_recognizable`,
                `is_shipping`
            FROM `credit_type`
            WHERE
                `store_id` = {OLD_STORE_ID};'''
    execute_query(wcnx, sql)


def clone_inventory_owner(wcnx):
    # old id is saved in description column
    sql = f'''INSERT INTO
                `inventory_owner` (
                    `store_id`, `owner_name`, `cost_center`, `description`, `api_token`, `status`, `created_by`, `created_at`, `updated_by`, `updated_at`
                )
            SELECT
                {NEW_STORE_ID},
                `owner_name`,
                `cost_center`,
                `id`,
                `api_token`,
                `status`,
                `created_by`,
                '{TODAY_DATE}',
                `updated_by`,
                '{TODAY_DATE}'
            FROM `inventory_owner`
            WHERE
                `store_id` = {OLD_STORE_ID};'''
    execute_query(wcnx, sql)


def get_product_ids(cnx):
#limit is set to 2 , need to update later
    sql = f'''
            SELECT id
            FROM `catalog`
            WHERE `store_id` = {OLD_STORE_ID};
        '''
    return execute_query(cnx, sql, False)


def clone_catalogs(cnx, product_ids):
    # old id is saved in item_note column
    sql = f'''INSERT INTO
                `catalog` (
                    `store_id`, `name`, `description`, `image`, `pre_sale_limit`, `public_name`, `public_description`, `status`, `is_for_display`, `is_retail`, `retail_price`, `is_taxable`, `is_pre_sale`, `is_promotional`, `is_max_qty_limit`, `max_qty`, `is_free`, `is_gift_item`, `tag`, `item_note`, `created_by`, `created_at`, `updated_by`, `updated_at`, `inventory_owner_id`, `list_order`, `inventory`, `is_external`, `external_link`, `is_global`, `non_vox_item`, `shipping_type`, `print_item`, `print_layout`, `is_on_sale`, `sale_price`, `auto_activate`
                )
            SELECT
                {NEW_STORE_ID},
                `name`,
                `description`,
                `image`,
                `pre_sale_limit`,
                `public_name`,
                `public_description`,
                `status`,
                `is_for_display`,
                `is_retail`,
                `retail_price`,
                `is_taxable`,
                `is_pre_sale`,
                `is_promotional`,
                `is_max_qty_limit`,
                `max_qty`,
                `is_free`,
                `is_gift_item`,
                `tag`,
                `id`,
                `created_by`,
                '{TODAY_DATE}',
                `updated_by`,
                '{TODAY_DATE}',
                (
                    SELECT id
                    from `inventory_owner`
                    WHERE
                        `description` = `inventory_owner_id`
                        AND store_id = {NEW_STORE_ID}
                    LIMIT 1
                ),
                `list_order`,
                `inventory`,
                `is_external`,
                `external_link`,
                `is_global`,
                `non_vox_item`,
                `shipping_type`,
                `print_item`,
                `print_layout`,
                `is_on_sale`,
                `sale_price`,
                `auto_activate`
            FROM `catalog`
            WHERE
                `id` IN {product_ids}
                AND `store_id` = {OLD_STORE_ID};'''

    execute_query(cnx, sql)


def clone_catalog_items(cnx, product_ids):
    sql = f'''INSERT INTO
                `catalog_item` (
                    `catalog_id`, `sku_number`, `cost`, `weight`, `presale_inventory`, `size`, `color`, `is_reorder_trigger`, `qoh`, `a2s`, `status`, `created_by`, `created_at`, `updated_by`, `updated_at`, `price`, `item_status`, `size_id`, `color_id`, `rank`
                )
            SELECT (
                    SELECT id
                    from `catalog`
                    WHERE
                        `item_note` = `catalog_id`
                    LIMIT 1
                ),
                `sku_number`,
                `cost`,
                `weight`,
                `presale_inventory`,
                `size`,
                `color`,
                `is_reorder_trigger`,
                `qoh`,
                `a2s`,
                `status`,
                `created_by`,
                '{TODAY_DATE}',
                `updated_by`,
                '{TODAY_DATE}',
                `price`,
                `item_status`,
                (
                    SELECT id
                    from `attribute`
                    WHERE
                        `list_order` = `size_id`
                        AND store_id = {NEW_STORE_ID}
                    LIMIT 1
                ),
                (
                    SELECT id
                    from `attribute`
                    WHERE
                        `list_order` = `color_id`
                        AND store_id = {NEW_STORE_ID}
                    LIMIT 1
                ),
                `rank`
            FROM `catalog_item`
            WHERE
                `catalog_id` IN {product_ids};'''

    execute_query(cnx, sql)


def clone_catalog_category(cnx, product_ids):
    sql = f'''INSERT INTO
                `catalog_category` (
                    `catalog_id`, `category_id`, `name`, `created_by`, `created_at`, `updated_by`, `updated_at`
                )
            SELECT (
                    SELECT id
                    from `catalog`
                    WHERE
                        `item_note` = `catalog_id`
                    LIMIT 1
                ),
                (
                    SELECT id
                    from `category`
                    WHERE
                        category.`list_order` = catalog_category.`category_id`
                    LIMIT 1
                ),
                `name`,
                `created_by`,
                '{TODAY_DATE}',
                `updated_by`,
                '{TODAY_DATE}'
            FROM `catalog_category`
            WHERE
                `catalog_id` IN {product_ids};'''
    execute_query(cnx, sql)


def clone_catalog_price(cnx, product_ids):
    sql = f'''INSERT INTO
                `catalog_price` (
                    `catalog_id`, `type_id`, `value`, `created_by`, `created_at`, `updated_by`, `updated_at`, `credit_currency_code`
                )
            SELECT (
                    SELECT id
                    from `catalog`
                    WHERE
                        `item_note` = `catalog_id`
                    LIMIT 1
                ),
                (
                    SELECT id
                    from `credit_type`
                    WHERE
                        `list_order` = `type_id`
                    LIMIT 1
                ),
                `value`,
                `created_by`,
                '{TODAY_DATE}',
                `updated_by`,
                '{TODAY_DATE}',
                `credit_currency_code`
            FROM `catalog_price`
            WHERE
                `catalog_id` IN {product_ids};'''
    execute_query(cnx, sql)


def clone_catalog_attributes(cnx, product_ids):
    sql = f'''INSERT INTO
                `catalog_attribute` (
                    `catalog_id`, `attribute_id`, `attribute_parent_id`, `name`, `created_at`, `created_by`, `updated_at`, `updated_by`
                )
            SELECT (
                    SELECT id
                    from `catalog`
                    WHERE
                        `item_note` = `catalog_id`
                    LIMIT 1
                ),
                (
                    SELECT id
                    from `attribute`
                    WHERE
                        `list_order` = `attribute_id`
                    LIMIT 1
                ),
                (
                    SELECT id
                    from `attribute`
                    WHERE
                        `list_order` = `attribute_parent_id`
                    LIMIT 1
                ),
                `name`,
               '{TODAY_DATE}',
                `created_by`,
                '{TODAY_DATE}',
                `updated_by`
            FROM `catalog_attribute`
            WHERE
                `catalog_id` IN {product_ids};
        '''

    execute_query(cnx, sql)


def clone_catalog_queues(cnx, product_ids):
    sql = f'''INSERT INTO
                `catalog_queue` (
                    `store_id`, `catalog_id`, `name`, `image`, `comment`, `created_by`, `created_at`, `updated_by`, `updated_at`, `deleted_at`
                )
            SELECT
                {NEW_STORE_ID},
                (
                    SELECT id
                    from `catalog`
                    WHERE
                        `item_note` = `catalog_id`
                    LIMIT 1
                ),
                `name`,
                `image`,
                `comment`,
                `created_by`,
                '{TODAY_DATE}',
                `updated_by`,
                '{TODAY_DATE}',
                `deleted_at`
            FROM `catalog_queue`
            WHERE
                `catalog_id` IN {product_ids};'''
    execute_query(cnx, sql)


def clone_catalog_images(cnx, product_ids):
    sql = f'''INSERT INTO
            `catalog_image` (
                `catalog_id`, `image`, `status`, `is_primary`, `created_by`, `created_at`, `updated_by`, `updated_at`, `deleted_at`, `list_order`, `color_id`
            )
        SELECT
            (
                SELECT id
                from `catalog`
                WHERE
                    `item_note` = `catalog_id`
                LIMIT 1
            ),
            `image`,
            `status`,
            `is_primary`,
            `created_by`,
            '{TODAY_DATE}',
            `updated_by`,
            '{TODAY_DATE}',
            `deleted_at`,
            `list_order`,
            `color_id`
        FROM `catalog_image`
        WHERE
            `catalog_id` IN {product_ids};'''
    execute_query(cnx, sql)


# Function to construct and execute an SQL query to update initiatives based on the current date
def construct(cnx, wcnx):

    # clone_attribute(wcnx)
    # clone_category(wcnx)
    # clone_credit_type(wcnx)
    # clone_inventory_owner(wcnx)

    get_ids = get_product_ids(cnx)

    for chunked_data in chunk(get_ids, 3):

        try:
            product_ids = tuple(d['id'] for d in chunked_data)

            clone_catalogs(wcnx, product_ids)

            clone_catalog_category(wcnx, product_ids)
            clone_catalog_items(wcnx, product_ids)
            clone_catalog_price(wcnx, product_ids)
            clone_catalog_attributes(wcnx, product_ids)
            clone_catalog_queues(wcnx, product_ids)
            clone_catalog_images(wcnx, product_ids)
        except:
            continue

    return "Cloned successfully."


# Lambda function handler


def lambda_handler(event, context):
    # Get a database connection for writing
    cnx = pms.get_reader_cnx('ecommMultiApi')
    wcnx = pms.get_writer_cnx('ecommMultiApi')
    try:
        resp = construct(cnx, wcnx)

        print(resp)
        return resp
    except:
        raise
    finally:
        wcnx.close()


lambda_handler(0, 0)













def insert_data_into_pick_bin_snapshot(reader, writer, customerId):
   
    result = fetch_pickbin_snapshot_from_inverntery(reader, writer,customerId)
    now = datetime.now(timezone("America/Denver")).strftime('%Y-%m-%d %H:%M:%S')
    created_date = datetime.now(timezone("America/Denver")).strftime('%Y-%m-%d')
    
    # Define the insert query for the target table
    insert_query = f"""
    INSERT INTO pick_bin_snapshots
    (customerId, itemSkuNumber, name, `rank`, itemQoh, isRetire, isCharged, isBillable, created_at, updated_at, type, location, created_date, loadNumber)
    VALUES (%(customerId)s, %(itemSkuNumber)s, %(name)s, %(rank)s, %(itemQoh)s, '0', '1', '1', '{now}', '{now}', %(type)s,  %(location)s, '{created_date}', %(loadNumber)s)
    """
    
    formatedResult = []

    print(result)
    if len(result) > 0:
        # for items in chunk(result, 1000):
        #     try:
        with writer.cursor() as cursor:
            cursor.executemany(insert_query, result)
            writer.commit()
            # except:
            #     pass
            
        for item in result:
            item['csv_generated_date'] = now
            item['type'] =  stateMap.get(str(item['type']), 'EmptyLocation')
            formatedResult.extend(item)
    return result