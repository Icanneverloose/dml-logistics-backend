from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import os

def wrap_text(text, max_chars=43):
    """Wrap text to multiple lines if longer than max_chars"""
    if len(text) <= max_chars:
        return [text]
    
    lines = []
    words = text.split(' ')
    current_line = ''
    
    for word in words:
        test_line = f"{current_line} {word}".strip() if current_line else word
        if len(test_line) <= max_chars:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            # If word itself is longer than max_chars, break it
            if len(word) > max_chars:
                remaining_word = word
                while len(remaining_word) > max_chars:
                    lines.append(remaining_word[:max_chars])
                    remaining_word = remaining_word[max_chars:]
                current_line = remaining_word
            else:
                current_line = word
    
    if current_line:
        lines.append(current_line)
    
    return lines if lines else [text]

def generate_pdf_receipt(shipment):
    """Generate PDF receipt for a shipment object"""
    try:
        # Create static/pdfs directory if it doesn't exist
        pdf_dir = os.path.join('static', 'pdfs')
        if not os.path.exists(pdf_dir):
            os.makedirs(pdf_dir)
        
        # Generate filename
        filename = f"{shipment.tracking_number}.pdf"
        file_path = os.path.join(pdf_dir, filename)
        
        # Create PDF
        c = canvas.Canvas(file_path, pagesize=letter)
        c.setFont("Helvetica", 12)

        # Title
        c.setFont("Helvetica-Bold", 16)
        c.drawString(100, 800, "SHIPMENT RECEIPT")
        c.setFont("Helvetica", 12)

        # Tracking Number
        c.drawString(100, 780, f"Tracking Number: {shipment.tracking_number}")

        # Sender Info
        y_pos = 760
        c.drawString(100, y_pos, f"Sender Name: {shipment.sender_name}")
        y_pos -= 15
        c.drawString(100, y_pos, f"Sender Email: {shipment.sender_email}")
        y_pos -= 15
        c.drawString(100, y_pos, f"Sender Phone: {shipment.sender_phone}")
        y_pos -= 15
        
        # Wrap sender address
        sender_address_lines = wrap_text(str(shipment.sender_address))
        c.drawString(100, y_pos, "Sender Address:")
        y_pos -= 15
        for line in sender_address_lines:
            c.drawString(120, y_pos, line)
            y_pos -= 15

        # Receiver Info
        y_pos -= 10  # Add spacing
        c.drawString(100, y_pos, f"Receiver Name: {shipment.receiver_name}")
        y_pos -= 15
        c.drawString(100, y_pos, f"Receiver Phone: {shipment.receiver_phone}")
        y_pos -= 15
        
        # Wrap receiver address
        receiver_address_lines = wrap_text(str(shipment.receiver_address))
        c.drawString(100, y_pos, "Receiver Address:")
        y_pos -= 15
        for line in receiver_address_lines:
            c.drawString(120, y_pos, line)
            y_pos -= 15

        # Package Info (adjust Y position based on address wrapping)
        y_pos -= 10  # Add spacing
        c.drawString(100, y_pos, f"Package Type: {shipment.package_type}")
        y_pos -= 15
        c.drawString(100, y_pos, f"Weight: {shipment.weight} kg")
        y_pos -= 15
        c.drawString(100, y_pos, f"Shipment Cost: ${shipment.shipment_cost}")

        # Status
        y_pos -= 15
        c.drawString(100, y_pos, f"Current Status: {shipment.status}")
        if shipment.estimated_delivery_date:
            y_pos -= 15
            c.drawString(100, y_pos, f"Estimated Delivery: {shipment.estimated_delivery_date.strftime('%Y-%m-%d')}")

        # Date
        y_pos -= 15
        if shipment.date_registered:
            c.drawString(100, y_pos, f"Date Created: {shipment.date_registered.strftime('%Y-%m-%d %H:%M:%S')}")

        c.save()
        
        # Return the relative path for storage in database
        return f"static/pdfs/{filename}"
        
    except Exception as e:
        print(f"Error generating PDF: {e}")
        # Return a default path or None if PDF generation fails
        return None
