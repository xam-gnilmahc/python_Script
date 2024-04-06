<?php

// IMAP server configuration
$imapPath = '{imap.gmail.com:993/imap/ssl}INBOX';
$username = 'maxrai788@gmail.com';
$password = 'rqcuswodywcazihj';

// Connect to the IMAP server
$inbox = imap_open($imapPath, $username, $password) or die('Failed to connect to Gmail');

// Check if the connection was successful
if ($inbox) {
    // Get today's date
    $today = date('d-M-Y');

    // Search for unread messages received today
    $emails = imap_search($inbox, 'UNSEEN SINCE "' . $today . '"');

    // Check if there are any unread messages
    if ($emails) {

        // Loop through each unread message
        foreach ($emails as $email_number) {
            // Fetch the message structure
            $message = imap_fetchbody($inbox, $email_number, '1'); 
            $subMessage = substr($message, 0, 200); 
            $finalMessage = trim(quoted_printable_decode($subMessage)); 
            $finalMessage = strip_tags($finalMessage);
            
            // Output the message content
            echo "Message content:";
            echo $finalMessage ;
            // Mark the message as read (optional)
            imap_setflag_full($inbox, $email_number, "\\Seen");
        }
    } else {
        echo "No unread messages found in your inbox";
    }

    // Close the connection to the IMAP server
    imap_close($inbox);
} else {
    echo "Failed to connect to Gmail";
}



// // Function to extract plain text from email message
// function getPlainTextFromMessage($inbox, $email_number, $structure) {
//     $message = "";
    
//     if (isset($structure->parts) && count($structure->parts) > 0) {
//         foreach ($structure->parts as $part_number => $part) {
//             // Check if the part is text/plain
//             if ($part->subtype == 'PLAIN') {
//                 // Fetch the plain text part
//                 $message = imap_fetchbody($inbox, $email_number, $part_number + 1);
//                 break;
//             } elseif ($part->subtype == 'HTML') {
//                 // Fetch the HTML part and remove HTML tags
//                 $htmlMessage = imap_fetchbody($inbox, $email_number, $part_number + 1);
//                 $message = strip_tags($htmlMessage);
//             }
//         }
//     }
    
//     return $message;
// }
?>
