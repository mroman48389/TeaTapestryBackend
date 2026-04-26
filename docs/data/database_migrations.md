# Steps for Performing a Database Migration

>    1. Run 
>
>           script\PowerShell\backup_db.ps1 
>
>       to create a backup or, in pgAdmin, go to
>
>           Servers --> PostgreSQL 18 --> Databases --> [database name] --> right-click --> Backup... 
>
>       and enter the full path to where you'd like to save the backup.
>
>    2. Generate an Alembic migration. Suppose we are dropping a price column. Then we might do:
>	
>	        alembic revision -m "Drop avg_price_per_oz_usd column from tea_profiles"
>	
>       This creates a new migration file under alembic/versions/[revision_id]_[file_name].py.
>
>    3. Edit the migration file. For example:
>
>     	    def upgrade():
>     	 	   op.drop_column('tea_profiles', 'price')
>
>           def downgrade():
>     		    op.add_column('tea_profiles', sa.Column('price', sa.Numeric(7, 2), nullable=True))
>
>    4. Apply the migration with
>
>     	    alembic upgrade head
>
>    5. Refresh the table in pgAdmin and confirm the change is applied.
