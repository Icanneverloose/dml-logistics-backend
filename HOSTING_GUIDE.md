# 🚀 Complete Hosting Guide for DML Logistics

## Recommended Setup: **Vercel (Frontend) + Render (Backend) + Cloudinary (Storage)**

---

## 📋 Table of Contents
1. [Frontend Deployment (Vercel)](#frontend-deployment-vercel)
2. [Backend Deployment (Render)](#backend-deployment-render)
3. [Database Setup (PostgreSQL)](#database-setup-postgresql)
4. [File Storage (Cloudinary)](#file-storage-cloudinary)
5. [Environment Variables](#environment-variables)
6. [Alternative Options](#alternative-options)

---

## 1. Frontend Deployment (Vercel)

### Why Vercel?
- ✅ Free tier with excellent performance
- ✅ Automatic SSL certificates
- ✅ Global CDN
- ✅ Easy GitHub integration
- ✅ Automatic deployments on push

### Setup Steps:

#### Step 1: Prepare Frontend for Production

1. **Update `vite.config.ts`** (if exists) or create it:
```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react-swc'

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: 'dist',
  },
})
```

2. **Create `.env.production`** in frontend root:
```env
VITE_API_BASE_URL=https://your-backend-url.onrender.com
```

#### Step 2: Deploy to Vercel

1. **Push frontend code to GitHub**
2. **Go to [vercel.com](https://vercel.com)** and sign up/login
3. **Click "New Project"**
4. **Import your GitHub repository** (the frontend folder)
5. **Configure:**
   - **Framework Preset:** Vite
   - **Root Directory:** `DML-Logistics-Project` (or your frontend folder name)
   - **Build Command:** `npm run build`
   - **Output Directory:** `dist`
   - **Environment Variables:**
     - `VITE_API_BASE_URL`: `https://your-backend-url.onrender.com`

6. **Click "Deploy"**
7. **Your frontend will be live at:** `https://your-project.vercel.app`

---

## 2. Backend Deployment (Render)

Since you already have the backend on Render, here's how to optimize it:

### Current Setup Issues to Fix:

#### A. Upgrade from SQLite to PostgreSQL

**Why?** SQLite files can be lost on Render when instances restart.

1. **Add PostgreSQL Database to Render:**
   - Go to your Render dashboard
   - Click "New +" → "PostgreSQL"
   - Name it: `dml-logistics-db`
   - Copy the **Internal Database URL**

2. **Update `app.py`:**
```python
# Change from SQLite to PostgreSQL
import os

# Get database URL from environment (Render provides this automatically)
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL or 'sqlite:///app.db'
```

3. **Update `requirements.txt`:**
```txt
Flask
Flask-Cors
Flask-SQLAlchemy
psycopg2-binary  # Add this for PostgreSQL
marshmallow
reportlab
qrcode
pillow
python-dotenv
sendgrid
cloudinary  # Add this for file storage
```

4. **Initialize database** (run this once locally or via Render shell):
```python
# Run this script once after deploying
from app import app, db
with app.app_context():
    db.create_all()
    print("Database tables created!")
```

#### B. Update Render Service Settings:

1. **Environment Variables** (in Render dashboard):
   ```
   FLASK_ENV=production
   FRONTEND_URL=https://your-frontend.vercel.app
   CLOUDINARY_URL=cloudinary://your-api-key:your-api-secret@your-cloud-name
   ```

2. **Build Command:**
   ```
   pip install -r requirements.txt
   ```

3. **Start Command:**
   ```
   gunicorn app:app
   ```

4. **Add `gunicorn` to `requirements.txt`:**
   ```
   gunicorn
   ```

---

## 3. File Storage (Cloudinary) - For PDF Receipts

### Why Cloudinary?
- ✅ Free tier: 25GB storage + 25GB bandwidth/month
- ✅ Built-in CDN for fast delivery
- ✅ Easy Python integration
- ✅ Automatic image optimization

### Setup Steps:

#### Step 1: Sign Up for Cloudinary
1. Go to [cloudinary.com](https://cloudinary.com)
2. Sign up for free account
3. Copy your credentials from Dashboard:
   - Cloud name
   - API Key
   - API Secret

#### Step 2: Install Cloudinary SDK
Already added to `requirements.txt` above: `cloudinary`

#### Step 3: Update PDF Generator

**Update `utils/pdf_generator.py`:**

```python
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import os
import cloudinary
import cloudinary.uploader
from io import BytesIO

# Configure Cloudinary (set these in environment variables)
cloudinary.config(
    cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME'),
    api_key=os.environ.get('CLOUDINARY_API_KEY'),
    api_secret=os.environ.get('CLOUDINARY_API_SECRET')
)

def generate_pdf_receipt(shipment):
    """Generate PDF receipt and upload to Cloudinary"""
    try:
        # Create PDF in memory instead of file system
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        c.setFont("Helvetica", 12)

        # Title
        c.setFont("Helvetica-Bold", 16)
        c.drawString(100, 800, "SHIPMENT RECEIPT")
        c.setFont("Helvetica", 12)

        # Tracking Number
        c.drawString(100, 780, f"Tracking Number: {shipment.tracking_number}")

        # Sender Info
        c.drawString(100, 760, f"Sender Name: {shipment.sender_name}")
        c.drawString(100, 745, f"Sender Email: {shipment.sender_email}")
        c.drawString(100, 730, f"Sender Phone: {shipment.sender_phone}")
        c.drawString(100, 715, f"Sender Address: {shipment.sender_address}")

        # Receiver Info
        c.drawString(100, 695, f"Receiver Name: {shipment.receiver_name}")
        c.drawString(100, 680, f"Receiver Phone: {shipment.receiver_phone}")
        c.drawString(100, 665, f"Receiver Address: {shipment.receiver_address}")

        # Package Info
        c.drawString(100, 645, f"Package Type: {shipment.package_type}")
        c.drawString(100, 630, f"Weight: {shipment.weight} kg")
        c.drawString(100, 615, f"Shipment Cost: ${shipment.shipment_cost}")

        # Status
        c.drawString(100, 595, f"Current Status: {shipment.status}")
        if shipment.estimated_delivery_date:
            c.drawString(100, 580, f"Estimated Delivery: {shipment.estimated_delivery_date.strftime('%Y-%m-%d')}")

        # Date
        c.drawString(100, 560, f"Date Created: {shipment.date_registered.strftime('%Y-%m-%d %H:%M:%S')}")

        c.save()
        buffer.seek(0)
        
        # Upload to Cloudinary
        filename = f"{shipment.tracking_number}.pdf"
        upload_result = cloudinary.uploader.upload(
            buffer,
            resource_type="raw",  # 'raw' for PDFs
            folder="receipts",  # Optional: organize in folder
            public_id=filename,
            format="pdf"
        )
        
        # Return the Cloudinary URL
        pdf_url = upload_result.get('secure_url')  # Use secure_url for HTTPS
        return pdf_url
        
    except Exception as e:
        print(f"Error generating/uploading PDF: {e}")
        return None
```

#### Step 4: Update Render Environment Variables

Add these to your Render service:
```
CLOUDINARY_CLOUD_NAME=your-cloud-name
CLOUDINARY_API_KEY=your-api-key
CLOUDINARY_API_SECRET=your-api-secret
```

#### Step 5: Update Frontend API Client

Your frontend already uses `getPdfUrl()` which should work, but make sure it handles full Cloudinary URLs:

**In `src/lib/api.ts`, the `getPdfUrl` function should handle both:**
- Relative paths: `static/pdfs/TRK123.pdf` → Convert to full URL
- Full URLs: `https://res.cloudinary.com/...` → Use as-is

```typescript
export function getPdfUrl(pdfPath: string | null | undefined): string | null {
  if (!pdfPath) return null;
  
  // If it's already a full URL (Cloudinary), return as-is
  if (pdfPath.startsWith('http://') || pdfPath.startsWith('https://')) {
    return pdfPath;
  }
  
  // If it's a relative path, prepend API base URL
  const baseUrl = API_BASE_URL.replace('/api', ''); // Remove /api suffix
  return `${baseUrl}/${pdfPath}`;
}
```

---

## 4. Environment Variables Summary

### Frontend (Vercel):
```
VITE_API_BASE_URL=https://your-backend.onrender.com
```

### Backend (Render):
```
FLASK_ENV=production
DATABASE_URL=postgresql://... (Auto-provided by Render)
FRONTEND_URL=https://your-frontend.vercel.app
CLOUDINARY_CLOUD_NAME=your-cloud-name
CLOUDINARY_API_KEY=your-api-key
CLOUDINARY_API_SECRET=your-api-secret
```

---

## 5. Alternative Hosting Options

### Option 2: Railway (All-in-One)
**Pros:**
- Simpler setup (everything in one place)
- PostgreSQL included
- $5/month starter plan (after free trial)

**Setup:**
1. Sign up at [railway.app](https://railway.app)
2. Create new project
3. Add PostgreSQL database
4. Deploy backend from GitHub
5. Deploy frontend as separate service
6. Use Railway volumes for file storage (or Cloudinary)

### Option 3: DigitalOcean App Platform
**Pros:**
- More control
- Spaces for file storage (S3-compatible)
- Starting at $5/month

**Setup:**
1. Create App Platform project
2. Add PostgreSQL database
3. Deploy backend
4. Deploy frontend
5. Create Spaces bucket for PDFs

### Option 4: AWS (Advanced)
**Services:**
- Frontend: AWS Amplify or S3 + CloudFront
- Backend: AWS Elastic Beanstalk or EC2
- Database: RDS PostgreSQL
- Storage: S3 for PDFs

**Cost:** Pay-as-you-go (~$10-50/month for small apps)

---

## 6. Cost Comparison

| Service | Free Tier | Paid Tier |
|---------|-----------|-----------|
| **Vercel (Frontend)** | ✅ Generous free tier | $20/month pro |
| **Render (Backend)** | ⚠️ Free (spins down) | $7/month always-on |
| **Cloudinary (Storage)** | ✅ 25GB free | $99/month for more |
| **Railway (All-in-one)** | ⚠️ $5 credit/month | $5-20/month |
| **DigitalOcean** | ❌ No free tier | $5/month minimum |

**Recommended Minimum Cost:** **$0/month** (with Render free tier limitations)
**Recommended Production Cost:** **$7/month** (Render paid) + Free tiers for others

---

## 7. Migration Checklist

- [ ] Push backend code to GitHub
- [ ] Push frontend code to GitHub
- [ ] Create PostgreSQL database on Render
- [ ] Update backend `app.py` for PostgreSQL
- [ ] Update `requirements.txt` with new packages
- [ ] Sign up for Cloudinary account
- [ ] Update PDF generator for Cloudinary
- [ ] Deploy backend to Render
- [ ] Deploy frontend to Vercel
- [ ] Update all environment variables
- [ ] Test PDF generation and storage
- [ ] Test frontend-backend connection
- [ ] Update CORS settings on backend

---

## 8. Support & Troubleshooting

### Common Issues:

1. **PDFs not loading:** Check Cloudinary URL format and CORS
2. **Database connection errors:** Verify DATABASE_URL format (postgresql:// not postgres://)
3. **CORS errors:** Ensure FRONTEND_URL is set correctly in backend
4. **Session not persisting:** Check cookie settings (sameSite, secure flags)

### Need Help?
- Render Docs: https://render.com/docs
- Vercel Docs: https://vercel.com/docs
- Cloudinary Docs: https://cloudinary.com/documentation

---

**🎉 You're all set! Your app will be live and production-ready!**


