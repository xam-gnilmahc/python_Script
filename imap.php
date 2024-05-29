<?php
use PHPMailer\PHPMailer\PHPMailer;
use PHPMailer\PHPMailer\Exception;
require 'vendor/autoload.php';

class ConnectionManager
{
    protected $username;
    protected $password;
    protected $host;
    protected $database;
    protected $user;
    protected $dbPassword;
    protected $imapPath;

    public function __construct($username, $password, $host, $database, $user, $dbPassword, $imapPath, $recipients)
    {
        $this->username = $username;
        $this->password = $password;
        $this->host = $host;
        $this->database = $database;
        $this->user = $user;
        $this->dbPassword = $dbPassword;
        $this->imapPath = $imapPath;
        $this->recipients = $recipients;
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
    protected function connectSMTP()
{
    $mail = new PHPMailer(true);
    try {
        //Server settings
        $mail->SMTPDebug = 0;                      // Enable verbose debug output
        $mail->isSMTP();                                            // Send using SMTP
        $mail->Host       = 'smtp.gmail.com';                     // Set the SMTP server to send through
        $mail->SMTPAuth   = true;                                   // Enable SMTP authentication
        $mail->Username   = $this->username;                         // SMTP username
        $mail->Password   = $this->password;                         // SMTP password
        $mail->SMTPSecure = 'tls';                                  // Enable TLS encryption; `PHPMailer::ENCRYPTION_SMTPS` encouraged
        $mail->Port       = 587;                                    // TCP port to connect to, use 465 for `PHPMailer::ENCRYPTION_SMTPS` above

        return $mail;
    } catch (Exception $e) {
        echo "SMTP connection failed. Error: {$e->getMessage()}";
        return null;
    }
}
}

class EmailHandler extends ConnectionManager
{

    public function readUnreadMessages($sinceDate)
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
            $messagesToSave = []; // Initialize an array to store all message bodies

            // Loop through each unread message, fetch its content, and mark it as read
            foreach ($emails as $emailNumber) {
                $message = imap_fetchbody($inbox, $emailNumber, '1');
                // Regular expression pattern to match unwanted lines
                // Regular expression pattern to match unwanted lines

                // Regular expression pattern to remove "On" lines
                //$pattern_on = '/(?:^|\n)On\s+\w{3},\s+\w{3}\s+\d{1,2},\s+\d{4}\s+at\s+\d{1,2}:\d{2}=E2=80=AFPM.*?(?=(\n\n|\z))|^-*\s+Forwarded\s+message\s+-*.*?(?=From:|$)/s';
                // $pattern_on = '/(?:^|\n)On\s+\w{3},\s+\w{3}\s+\d{1,2},\s+\d{4}\s+at\s+\d{1,2}:\d{2}=E2=80=AFPM.*?(?=(\n\n|\z))|^-*\s+Forwarded\s+message\s+-*.*?(?=From:|$)/s';
                $pattern_on = '/^(?:On\s+\w{3},\s+\w{3}\s+\d{1,2},\s+\d{4}\s+at\s+\d{1,2}:\d{2}=E2=80=AFPM.*|-*\s+Forwarded\s+message\s+-*|From:|To:|Date:|Subject:).*?(?=\n|$)/sm';

                // $pattern_on = '/(?:^|\n)On\s+\w{3},\s+\w{3}\s+\d{1,2},\s+\d{4}\s+at\s+\d{1,2}:\d{2}=E2=80=AFPM.*?(?=(\n|$))|^-*\s+Forwarded\s+message\s+-*.*?(?=(\n|$))/s';

                
                $mainContent = preg_replace($pattern_on, '', $message);
                $mainContent = trim($mainContent);
                $messagesToSave[] = $mainContent;
                // Print the main content
                // echo $mainContent . "\n";
            }
            $this->saveMessageToDatabase($messagesToSave);
            $this->exportMessagesToCSV($messagesToSave);
        } catch (Exception $e) {
            echo 'Error: ' . $e->getMessage() . "\n";
        } finally {
            // Disconnect from the IMAP server
            $this->disconnectIMAP($inbox);
        }
    }


    public function saveMessageToDatabase($messages)
    {
        try {
            $sql = "INSERT INTO pick_bin_snapshot_records (name, created_at, updated_at, created_date) VALUES ";
            $placeholders = implode(', ', array_fill(0, count($messages), "(?, NOW(), NOW(), NOW())"));
            $sql .= $placeholders;
            $params = [];

            foreach ($messages as $message) {

                // Add the message body to the parameters
                $params[] = $message;
            }

            // Generate the types string for binding parameters
            $types = str_repeat('s', count($params));

            // Execute the query
            $stmt = $this->executeQuery($sql, $params, $types);
            if ($this->checkIfRowsExist($stmt)) {
                echo "Messages saved to database successfully\n";
            } else {
                echo "Failed to save messages to database\n";
            }
        } catch (Exception $e) {
            echo 'Error: ' . $e->getMessage() . "\n";
        }
    }

    public function exportMessagesToCSV($messages)
    {
        try {
            // Generate CSV file path
            $csvFilePath = 'D:/task/tasks_' . date('YmdHis') . '.csv';
            // Open CSV file for writing
            $csvFile = fopen($csvFilePath, 'w');

            // Write CSV header
            fputcsv($csvFile, ['Message']);

            foreach ($messages as $message) {
                // Add the message to the CSV file
                fputcsv($csvFile, [$message]);
            }

            // Close CSV file
            fclose($csvFile);
            $this->sendEmailWithAttachment($csvFilePath, $this->recipients);


            echo "Messages exported to CSV file successfully: $csvFilePath\n";
        } catch (Exception $e) {
            echo 'Error: ' . $e->getMessage() . "\n";
        }
    }
    public function sendEmailWithAttachment($attachmentPath, $recipients)
    {
        try {
            $mail=$this->connectSMTP();
            //Recipients
            foreach ($recipients as $recipient) {
                $mail->addAddress($recipient);
            }
            //Attachments
            $mail->addAttachment($attachmentPath);         // Add attachments
            // Content
            $mail->isHTML(true);                                  // Set email format to HTML
            $mail->Body    = "inbox csvf file";
    
            $mail->send();
            echo 'Email has been sent successfully';
        } catch (Exception $e) {
            echo "Email could not be sent. Mailer Error: {$mail->ErrorInfo}";
        }
    }


}


$username = 'maxrai788@gmail.com';
$password = 'rqcuswodywcazihj';
$host = 'localhost';
$database = 'tdm';
$user = 'root';
$dbPassword = '123';
$imapPath = '{imap.gmail.com:993/imap/ssl}INBOX';
$sinceDate = date('d-M-Y');
$recipients = ["maxrai788@gmail.com", "max.c@shikhartech.com"];

$emailHandler = new EmailHandler($username, $password, $host, $database, $user, $dbPassword, $imapPath, $recipients);
$emailHandler->readUnreadMessages($sinceDate);
