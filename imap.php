<?php

class ConnectionManager
{
    protected $username;
    protected $password;
    protected $host;
    protected $database;
    protected $user;
    protected $dbPassword;
    protected $imapPath;

    public function __construct($username, $password, $host, $database, $user, $dbPassword, $imapPath)
    {
        $this->username = $username;
        $this->password = $password;
        $this->host = $host;
        $this->database = $database;
        $this->user = $user;
        $this->dbPassword = $dbPassword;
        $this->imapPath = $imapPath;
    }

    protected function connectDatabase()
    {
        // Connect to the database
        $mysqli = new mysqli($this->host, $this->user, $this->dbPassword, $this->database);

        // Check connection
        if ($mysqli->connect_errno) {
            throw new Exception("Failed to connect to MySQL: " . $mysqli->connect_error);
        }

        return $mysqli;
    }
    protected function executeQuery($sql, $params, $types = "")
    {
        try {
            // Connect to the database
            $mysqli = $this->connectDatabase();

            // Prepare the SQL statement
            $stmt = $mysqli->prepare($sql);

            // Bind parameters if types and parameters are provided
            if (!empty($types) && !empty($params)) {
                $stmt->bind_param($types, ...$params);
            }

            // Execute the statement
            $stmt->execute();
            return $stmt;
        } catch (Exception $e) {
            echo 'Error: ' . $e->getMessage() . "\n";
        }
    }
    protected function checkIfRowsExist($stmt)
    {
        return $stmt->affected_rows > 0;
    }
    protected function connectIMAP()
    {
        // Connect to the IMAP server
        $inbox = imap_open($this->imapPath, $this->username, $this->password);
        if (!$inbox) {
            throw new Exception('Failed to connect to Gmail');
        }
        return $inbox;
    }

    protected function disconnectIMAP($inbox)
    {
        // Close the connection to the IMAP server
        if ($inbox) {
            imap_close($inbox);
        }
    }
}

class EmailHandler extends ConnectionManager
{
    public function readUnreadMessages($sinceDate, $maxLength = 200)
    {
        try {
            // Connect to the IMAP server
            $inbox = $this->connectIMAP();

            // Search for unread messages received since the specified date
            $emails = imap_search($inbox, 'UNSEEN SINCE "' . $sinceDate . '"');
            if (!$emails) {
                echo "No unread messages found in your inbox\n";
                return;
            }
            $finalMessage = [];
            // Loop through each unread message, fetch its content, and mark it as read
            foreach ($emails as $emailNumber) {
                $message = imap_fetchbody($inbox, $emailNumber, '1');
                $subMessage = substr($message, 0, $maxLength);
                $finalMessage = trim(quoted_printable_decode($subMessage));
                $finalMessage = strip_tags($finalMessage);
                $this->saveMessageToDatabase($finalMessage);
            }
        } catch (Exception $e) {
            echo 'Error: ' . $e->getMessage() . "\n";
        } finally {
            // Disconnect from the IMAP server
            $this->disconnectIMAP($inbox);
        }
    }

    public function saveMessageToDatabase($message)
    {
        try {
            $sql = "INSERT INTO pick_bin_snapshot_records (name, created_at, updated_at, created_date) VALUES (?, NOW(), NOW(), NOW())";
            // Connect to the database
            $params = [$message];
            $types = "s";
            $stmt = $this->executeQuery($sql, $params, $types);
            if ($this->checkIfRowsExist($stmt)) {
                echo "Message saved to database successfully\n";
            } else {
                echo "Failed to save message to database\n";
            }
        } catch (Exception $e) {
            echo 'Error: ' . $e->getMessage() . "\n";
        }
    }
}


$username = 'maxrai788@gmail.com';
$password = 'rqcuswodywcazihj';
$host = 'localhost';
$database = 'tdm';
$user = 'root';
$dbPassword = '';
$imapPath = '{imap.gmail.com:993/imap/ssl}INBOX';
$sinceDate = date('d-M-Y');
$emailHandler = new EmailHandler($username, $password, $host, $database, $user, $dbPassword, $imapPath);
$emailHandler->readUnreadMessages($sinceDate);
