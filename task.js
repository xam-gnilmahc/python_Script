'use strict';
let mysql = require('mysql');

let pool = mysql.createPool({
  host         : "127.0.0.1",
  user         : "root",
  password     : "123",
  database     : "tdm",
  port         : 3306,
  queueLimit   : 0, // unlimited queueing
  connectionLimit : 0 // unlimited connections 
});  

const testConnection = async () => {
  try {
    var sql = `SELECT name,
    CAST(COUNT(CASE WHEN status = '1' THEN id  END) AS UNSIGNED) AS active_count,
    CAST(COUNT(CASE WHEN status = '0' THEN id END) AS UNSIGNED) AS inactive_count,
    COUNT(*) AS count , created_at FROM pick_bin_snapshot_records GROUP BY name`;
    const getData = await performDBQuery(sql, []);

    if (getData.length > 0) {
      console.log("Fetched data successfully:");
      const jsonData = getData.map(row => {
        return {
          name: row.name,
          total: row.count,
          created_at:row.created_at,
          active_count : row.active_count,
          inactive_count :row.inactive_count
        };
      });
      console.log(jsonData);
      return jsonData;
    } else {
      console.log("No data found.");
      return [];
    }
  } catch (error) {
    console.error(error);
    return [];
  }
}

const performDBQuery = async (sql, params) => {
  return new Promise((resolve, reject) => {
    pool.getConnection((err, connection) => {
      if (err) {
        reject(err);
      }
      connection.query(sql, params, (err, results) => {
        if (err) { 
          reject(err); 
        }
        connection.release();
        resolve(results);
      });
    });
  });
};

testConnection();
