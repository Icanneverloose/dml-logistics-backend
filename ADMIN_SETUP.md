# Admin Authentication Setup

## Overview
This application now has a working admin authentication system. Only users with the `role: 'admin'` can access admin routes and perform admin actions.

## How to Make a User Admin

### Method 1: Using the make_admin.py Script

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Run the script with the user's email:
   ```bash
   python make_admin.py user@example.com
   ```

   Example:
   ```bash
   python make_admin.py test@example.com
   ```

3. The user will now have admin privileges. They need to log out and log back in for the changes to take effect.

### Method 2: Manual Edit

1. Open `backend/data/users.json`
2. Find the user by their email or user ID
3. Add or update the `role` field to `"admin"`:
   ```json
   {
     "id": "user-id-here",
     "email": "user@example.com",
     "name": "User Name",
     "password": "...",
     "role": "admin",
     "created_at": "..."
   }
   ```

## Protected Routes

### Backend Routes (require admin role):
- `GET /api/shipments/all` - View all shipments
- `PUT /api/shipments/<tracking_number>/status` - Update shipment status
- `PUT /api/content/<section>` - Update content sections
- `POST /api/content` - Create content sections
- `DELETE /api/content/<section>` - Delete content sections

### Frontend Routes (require admin role):
- `/admin` - Admin Dashboard
- `/admin/shipments` - Manage shipments
- `/admin/fleet` - Fleet management
- `/admin/customers` - Customer management
- `/admin/reports` - Reports

## How It Works

1. **Backend**: 
   - Checks user session and verifies role in `utils/auth_utils.py`
   - Returns 403 Forbidden if user is not admin

2. **Frontend**:
   - `AdminProtectedRoute` component checks if user is logged in and has admin role
   - Redirects to login if not authenticated
   - Redirects to dashboard if authenticated but not admin

3. **User Role**:
   - Default role for new users: `"user"`
   - Admin role: `"admin"`
   - Role is stored in `backend/data/users.json`

## Testing Admin Access

1. Create or login with a regular user account
2. Try to access `/admin` - should redirect to dashboard
3. Make the user admin using `make_admin.py`
4. Log out and log back in
5. Try to access `/admin` - should now work!

## Notes

- Users need to log out and log back in after being granted admin privileges for the role to be updated in their session
- All new users are created with `role: 'user'` by default
- The role field is automatically added to existing users when they log in (defaults to 'user')

