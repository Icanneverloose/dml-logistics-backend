# Database Migration Guide

## Adding created_by Fields to Shipments

This migration adds `created_by` and `created_by_email` fields to the shipments table to track which user created each shipment.

### Why This Migration?

The new fields allow:
- **Managers** to see only shipments they created
- **Super Admins** to see all shipments (including those created by managers)
- **Support** to see shipments they created (if any)

### Running the Migration

#### Option 1: Using the Migration Script (Recommended)

```bash
cd backend
python run_migration.py
```

This will:
1. Check if the columns already exist
2. Add them if they don't exist
3. Handle both SQLite and PostgreSQL databases

#### Option 2: Manual Migration (SQLite)

If you're using SQLite and the script doesn't work, you can manually run:

```sql
ALTER TABLE shipments ADD COLUMN created_by VARCHAR(100);
ALTER TABLE shipments ADD COLUMN created_by_email VARCHAR(100);
```

#### Option 3: For PostgreSQL/MySQL

```sql
ALTER TABLE shipments ADD COLUMN created_by VARCHAR(100);
ALTER TABLE shipments ADD COLUMN created_by_email VARCHAR(100);
```

### After Migration

1. **Restart your backend server**
2. **Test shipment creation** as a manager
3. **Verify** that managers can see their own shipments
4. **Verify** that super admins can see all shipments

### Troubleshooting

If you see errors like:
- `no such column: created_by`
- `column created_by does not exist`

**Solution**: Run the migration script again or manually add the columns using SQL.

### Notes

- Existing shipments will have `NULL` values for `created_by` and `created_by_email`
- Managers won't see old shipments (created before migration) until they create new ones
- The backend will automatically handle missing columns gracefully (with a warning)

