from flask import Blueprint, request, jsonify
import os
import sendgrid
from sendgrid.helpers.mail import Mail, Email, To, Content
import urllib.error
import json
import requests

contact_bp = Blueprint('contact_bp', __name__)

@contact_bp.route('/quote', methods=['POST', 'OPTIONS'])
def submit_quote():
    """Handle contact form quote requests"""
    if request.method == 'OPTIONS':
        return jsonify({'ok': True}), 200
    
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('name') or not data.get('email') or not data.get('message'):
            return jsonify({
                'success': False,
                'error': 'Name, email, and message are required'
            }), 400
        
        # Get SendGrid API key from environment
        sendgrid_api_key = os.environ.get('SENDGRID_API_KEY')
        
        if not sendgrid_api_key:
            # Fallback: Log the request (for development)
            print("=" * 50)
            print("NEW QUOTE REQUEST (SendGrid not configured)")
            print("=" * 50)
            print(f"Name: {data.get('name', 'N/A')}")
            print(f"Email: {data.get('email', 'N/A')}")
            print(f"Phone: {data.get('phone', 'N/A')}")
            print(f"Company: {data.get('company', 'N/A')}")
            print(f"Service: {data.get('service', 'N/A')}")
            print(f"Message: {data.get('message', 'N/A')}")
            print("=" * 50)
            
            return jsonify({
                'success': True,
                'message': 'Your message has been received. We will get back to you soon!'
            })
        
        # Prepare email content
        subject = f"New Quote Request from {data.get('name', 'Customer')}"
        
        email_body = f"""New Quote Request Received

Name: {data.get('name', 'N/A')}
Email: {data.get('email', 'N/A')}
Phone: {data.get('phone', 'N/A')}
Company: {data.get('company', 'N/A')}
Service Interested In: {data.get('service', 'N/A')}

Message:
{data.get('message', 'N/A')}

---
This email was sent from the DML Logistics contact form.
Reply directly to this email to respond to the customer.
"""
        
        # Send email using SendGrid
        sg = sendgrid.SendGridAPIClient(api_key=sendgrid_api_key)
        
        from_email = Email(os.environ.get('SENDGRID_FROM_EMAIL', 'Info@dmllogisticsxpress.com'))
        to_email = To('contact@dmllogisticsxpress.com')
        content = Content("text/plain", email_body)
        
        message = Mail(
            from_email=from_email,
            to_emails=to_email,
            subject=subject,
            plain_text_content=content
        )
        
        # Set reply-to to customer's email
        message.reply_to = Email(data.get('email'))
        
        try:
            response = sg.send(message)
            
            if response.status_code in [200, 201, 202]:
                return jsonify({
                    'success': True,
                    'message': 'Your message has been sent successfully. We will get back to you soon!'
                })
            else:
                # Get error details from response
                error_body = response.body.decode('utf-8') if response.body else 'Unknown error'
                print(f"SendGrid error: Status {response.status_code}")
                print(f"Error body: {error_body}")
                
                # Parse error message if possible
                try:
                    error_data = json.loads(error_body)
                    error_message = error_data.get('errors', [{}])[0].get('message', 'Unknown SendGrid error')
                except:
                    error_message = f'SendGrid API error (Status {response.status_code})'
                
                # Check for specific error codes
                if response.status_code == 403:
                    return jsonify({
                        'success': False,
                        'error': 'Email sending failed: The sender email (Info@dmllogisticsxpress.com) is not verified in SendGrid. Please verify your sender email in SendGrid settings at https://app.sendgrid.com/settings/sender_auth/senders'
                    }), 500
                elif response.status_code == 401:
                    return jsonify({
                        'success': False,
                        'error': 'Email sending failed: Invalid SendGrid API key. Please check your SENDGRID_API_KEY in the .env file.'
                    }), 500
                else:
                    return jsonify({
                        'success': False,
                        'error': f'Failed to send email: {error_message}'
                    }), 500
                
        except requests.exceptions.HTTPError as http_error:
            # Handle HTTP errors from SendGrid (requests library)
            error_code = http_error.response.status_code if hasattr(http_error, 'response') else None
            error_msg = str(http_error)
            print(f"SendGrid HTTP error: Code {error_code}, Message: {error_msg}")
            
            # Try to get error details from response
            error_details = ''
            if hasattr(http_error, 'response') and http_error.response:
                try:
                    error_body = http_error.response.text
                    error_data = json.loads(error_body)
                    if 'errors' in error_data and len(error_data['errors']) > 0:
                        error_details = error_data['errors'][0].get('message', '')
                except:
                    pass
            
            if error_code == 403:
                # Always use our custom message with the correct email, even if SendGrid provides details
                return jsonify({
                    'success': False,
                    'error': 'Email sending failed: The sender email (Info@dmllogisticsxpress.com) is not verified in SendGrid. Please verify your sender email in SendGrid settings at https://app.sendgrid.com/settings/sender_auth/senders'
                }), 500
            elif error_code == 401:
                return jsonify({
                    'success': False,
                    'error': 'Email sending failed: Invalid SendGrid API key. Please check your SENDGRID_API_KEY in the .env file.'
                }), 500
            else:
                return jsonify({
                    'success': False,
                    'error': f'Email sending failed: HTTP {error_code} - {error_msg}'
                }), 500
                
        except urllib.error.HTTPError as http_error:
            # Handle HTTP errors from urllib (if SendGrid uses it)
            error_code = http_error.code
            error_msg = str(http_error)
            print(f"SendGrid HTTP error (urllib): Code {error_code}, Message: {error_msg}")
            
            if error_code == 403:
                return jsonify({
                    'success': False,
                    'error': 'Email sending failed: The sender email (Info@dmllogisticsxpress.com) is not verified in SendGrid. Please verify your sender email in SendGrid settings at https://app.sendgrid.com/settings/sender_auth/senders'
                }), 500
            elif error_code == 401:
                return jsonify({
                    'success': False,
                    'error': 'Email sending failed: Invalid SendGrid API key. Please check your SENDGRID_API_KEY in the .env file.'
                }), 500
            else:
                return jsonify({
                    'success': False,
                    'error': f'Email sending failed: HTTP {error_code} - {error_msg}'
                }), 500
                
        except Exception as sg_error:
            # Handle other SendGrid-related exceptions
            error_msg = str(sg_error)
            print(f"SendGrid exception: {error_msg}")
            
            # Check for specific error types in the message
            if '403' in error_msg or 'Forbidden' in error_msg:
                return jsonify({
                    'success': False,
                    'error': 'Email sending failed: The sender email (Info@dmllogisticsxpress.com) is not verified in SendGrid. Please verify your sender email in SendGrid settings at https://app.sendgrid.com/settings/sender_auth/senders'
                }), 500
            elif '401' in error_msg or 'Unauthorized' in error_msg:
                return jsonify({
                    'success': False,
                    'error': 'Email sending failed: Invalid SendGrid API key. Please check your SENDGRID_API_KEY in the .env file.'
                }), 500
            else:
                return jsonify({
                    'success': False,
                    'error': f'Email sending failed: {error_msg}'
                }), 500
        
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Failed to send message: {str(e)}'
        }), 500

