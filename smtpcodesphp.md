<?php
/**
 * Forgot Password Request API
 * Version: 1.0.0
 * 
 * This API endpoint handles password reset requests.
 * It generates a secure token and sends a reset link via email.
 * 
 * Method: POST
 * Parameters: 
 *   - email: User's email address
 * 
 * Response:
 *   - success: true/false
 *   - message: Status message
 */

error_reporting(E_ALL);
ini_set('display_errors', 1);

header("Content-Type: application/json");
header("Access-Control-Allow-Origin: *");
header("Access-Control-Allow-Methods: POST, OPTIONS");
header("Access-Control-Allow-Headers: Content-Type, Authorization");

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit();
}

// Database credentials
$host     = "localhost";
$dbname   = "u529002218_app";
$username = "u529002218_app";
$password = "Admin$12345";

/**
 * Send email using SMTP with settings from database
 */
function sendResetEmail($conn, $to_email, $to_name, $reset_token) {
    try {
        // Fetch SMTP settings from database
        $smtp_settings = [];
        $sql = "SELECT name, value FROM settings WHERE name IN ('smtp_host', 'smtp_port', 'smtp_username', 'smtp_password', 'smtp_encryption', 'site_title', 'company_email')";
        $result = $conn->query($sql);
        
        if ($result) {
            while ($row = $result->fetch_assoc()) {
                $smtp_settings[$row['name']] = $row['value'];
            }
        }
        
        // Default values if not found in database
        $smtp_host = isset($smtp_settings['smtp_host']) ? $smtp_settings['smtp_host'] : 'smtp.hostinger.com';
        $smtp_port = isset($smtp_settings['smtp_port']) ? $smtp_settings['smtp_port'] : 465;
        $smtp_username = isset($smtp_settings['smtp_username']) ? $smtp_settings['smtp_username'] : 'registration@sabkapaisa.com';
        $smtp_password = isset($smtp_settings['smtp_password']) ? $smtp_settings['smtp_password'] : 'Admin$12345';
        $smtp_encryption = isset($smtp_settings['smtp_encryption']) ? $smtp_settings['smtp_encryption'] : 'ssl';
        $site_title = isset($smtp_settings['site_title']) ? $smtp_settings['site_title'] : 'SabkaPaisa';
        $from_email = isset($smtp_settings['company_email']) ? $smtp_settings['company_email'] : $smtp_username;
        
        // Generate reset URL (adjust domain as needed)
        $reset_url = "https://" . $_SERVER['HTTP_HOST'] . "/finance/password/reset/" . $reset_token . "?email=" . urlencode($to_email);
        
        // Try to use PHPMailer if available
        $phpmailer_path = dirname(__DIR__) . '/vendor/autoload.php';
        
        if (file_exists($phpmailer_path)) {
            require_once $phpmailer_path;
            
            if (class_exists('PHPMailer\PHPMailer\PHPMailer')) {
                $mail = new PHPMailer\PHPMailer\PHPMailer(true);
                
                // Server settings
                $mail->isSMTP();
                $mail->Host       = $smtp_host;
                $mail->SMTPAuth   = true;
                $mail->Username   = $smtp_username;
                $mail->Password   = $smtp_password;
                $mail->SMTPSecure = $smtp_encryption;
                $mail->Port       = $smtp_port;
                $mail->CharSet    = 'UTF-8';
                
                // Recipients
                $mail->setFrom($from_email, $site_title);
                $mail->addAddress($to_email, $to_name);
                
                // Content
                $mail->isHTML(true);
                $mail->Subject = 'Reset Your Password - ' . $site_title;
                
                $email_body = "
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset='UTF-8'>
                    <style>
                        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }
                        .content { background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }
                        .button { display: inline-block; padding: 15px 30px; background: #667eea; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; font-weight: bold; }
                        .footer { text-align: center; margin-top: 20px; color: #666; font-size: 12px; }
                        .warning { background: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 20px 0; }
                    </style>
                </head>
                <body>
                    <div class='container'>
                        <div class='header'>
                            <h1>🔐 Password Reset Request</h1>
                        </div>
                        <div class='content'>
                            <p>Hello <strong>" . htmlspecialchars($to_name) . "</strong>,</p>
                            
                            <p>We received a request to reset the password for your account associated with this email address.</p>
                            
                            <p>Click the button below to reset your password:</p>
                            
                            <div style='text-align: center;'>
                                <a href='" . $reset_url . "' class='button'>Reset Password</a>
                            </div>
                            
                            <p>Or copy and paste this link into your browser:</p>
                            <p style='word-break: break-all; background: #fff; padding: 10px; border: 1px solid #ddd; border-radius: 5px;'>
                                " . $reset_url . "
                            </p>
                            
                            <div class='warning'>
                                <strong>⚠️ Security Notice:</strong>
                                <ul>
                                    <li>This link will expire in 60 minutes</li>
                                    <li>If you didn't request this, please ignore this email</li>
                                    <li>Your password will remain unchanged</li>
                                </ul>
                            </div>
                            
                            <p>If you have any questions or concerns, please contact our support team.</p>
                            
                            <p>Best regards,<br><strong>" . $site_title . " Team</strong></p>
                        </div>
                        <div class='footer'>
                            <p>This is an automated email. Please do not reply to this message.</p>
                            <p>&copy; " . date('Y') . " " . $site_title . ". All rights reserved.</p>
                        </div>
                    </div>
                </body>
                </html>
                ";
                
                $mail->Body = $email_body;
                $mail->AltBody = "Hello " . $to_name . ",\n\nWe received a request to reset your password. Click the link below to reset it:\n\n" . $reset_url . "\n\nThis link will expire in 60 minutes. If you didn't request this, please ignore this email.\n\nBest regards,\n" . $site_title;
                
                $mail->send();
                return true;
            }
        }
        
        // Fallback to PHP mail() function
        $subject = 'Reset Your Password - ' . $site_title;
        $headers = "MIME-Version: 1.0" . "\r\n";
        $headers .= "Content-type:text/html;charset=UTF-8" . "\r\n";
        $headers .= "From: " . $from_email . "\r\n";
        
        $message = "Hello " . htmlspecialchars($to_name) . ",\n\n";
        $message .= "We received a request to reset your password. Click the link below:\n\n";
        $message .= $reset_url . "\n\n";
        $message .= "This link will expire in 60 minutes.\n\n";
        $message .= "If you didn't request this, please ignore this email.\n\n";
        $message .= "Best regards,\n" . $site_title;
        
        return mail($to_email, $subject, $message, $headers);
        
    } catch (Exception $e) {
        error_log("Email sending failed: " . $e->getMessage());
        return false;
    }
}

/**
 * Generate a secure random token
 */
function generateSecureToken($length = 64) {
    return bin2hex(random_bytes($length / 2));
}

try {
    // Only allow POST requests
    if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
        http_response_code(405);
        throw new Exception("Method not allowed. Use POST.");
    }
    
    // Connect to database
    $conn = new mysqli($host, $username, $password, $dbname);
    
    if ($conn->connect_error) {
        throw new Exception("Database connection failed");
    }
    
    $conn->set_charset("utf8mb4");
    
    // Get input JSON
    $input = file_get_contents("php://input");
    $data = json_decode($input, true);
    
    if (json_last_error() !== JSON_ERROR_NONE) {
        throw new Exception("Invalid JSON format");
    }
    
    // Validate email
    $email = isset($data['email']) ? trim($data['email']) : '';
    
    if (empty($email)) {
        http_response_code(400);
        throw new Exception("Email address is required");
    }
    
    if (!filter_var($email, FILTER_VALIDATE_EMAIL)) {
        http_response_code(400);
        throw new Exception("Invalid email address format");
    }
    
    // Check if user exists
    $sql = "SELECT id, name, email, status FROM users WHERE email = ? LIMIT 1";
    $stmt = $conn->prepare($sql);
    
    if (!$stmt) {
        throw new Exception("Database prepare failed");
    }
    
    $stmt->bind_param("s", $email);
    $stmt->execute();
    $result = $stmt->get_result();
    
    if ($result->num_rows === 0) {
        // For security, don't reveal if email exists or not
        // Return success message anyway
        http_response_code(200);
        echo json_encode([
            "success" => true,
            "message" => "If your email is registered, you will receive a password reset link shortly.",
            "timestamp" => date('Y-m-d H:i:s')
        ], JSON_PRETTY_PRINT);
        exit();
    }
    
    $user = $result->fetch_assoc();
    $stmt->close();
    
    // Check if user is active
    if ($user['status'] != 1) {
        http_response_code(403);
        throw new Exception("Your account is inactive. Please contact support.");
    }
    
    // Delete any existing password reset tokens for this email
    $sql_delete = "DELETE FROM password_resets WHERE email = ?";
    $stmt_delete = $conn->prepare($sql_delete);
    $stmt_delete->bind_param("s", $email);
    $stmt_delete->execute();
    $stmt_delete->close();
    
    // Generate secure token
    $token = generateSecureToken();
    $hashed_token = password_hash($token, PASSWORD_BCRYPT);
    
    // Insert new password reset token
    $sql_insert = "INSERT INTO password_resets (email, token, created_at) VALUES (?, ?, NOW())";
    $stmt_insert = $conn->prepare($sql_insert);
    
    if (!$stmt_insert) {
        throw new Exception("Failed to create password reset request");
    }
    
    $stmt_insert->bind_param("ss", $email, $hashed_token);
    
    if (!$stmt_insert->execute()) {
        throw new Exception("Failed to save password reset token");
    }
    
    $stmt_insert->close();
    
    // Send password reset email
    $email_sent = sendResetEmail($conn, $user['email'], $user['name'], $token);
    
    if (!$email_sent) {
        // Log error but don't reveal to user
        error_log("Failed to send password reset email to: " . $email);
    }
    
    // Always return success for security reasons
    http_response_code(200);
    echo json_encode([
        "success" => true,
        "message" => "If your email is registered, you will receive a password reset link shortly.",
        "details" => [
            "email_sent" => $email_sent,
            "note" => "Please check your email inbox and spam folder"
        ],
        "timestamp" => date('Y-m-d H:i:s')
    ], JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE);
    
} catch (Exception $e) {
    $errorCode = http_response_code() ?: 500;
    echo json_encode([
        "success" => false,
        "message" => $e->getMessage(),
        "error_code" => $errorCode,
        "timestamp" => date('Y-m-d H:i:s')
    ], JSON_PRETTY_PRINT);
} finally {
    if (isset($conn)) {
        $conn->close();
    }
}
?>