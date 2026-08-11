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
>    2. If adding a new table to the database, after adding the model in src/db/models (and schema, 
>       if applicable, in src/api/schemas), add an import to alembic/env.py so alembic knows about
>       the new model. Be sure to add  "# noqa: F401" at the end of the import so the linter
>       does not remove it.
>
>    3. Generate an Alembic migration. Suppose we are dropping a price column. Then we might do:
>	
>	        alembic revision -m "Drop avg_price_per_oz_usd column from tea_profiles"
>	
>       This creates a new migration file under alembic/versions/[revision_id]_[file_name].py.
>
>    4. Edit the migration file, if needed. It's critical to check and make sure it will do what you
>       expect! For example, if you add a new column, you should see:
>
>     	    def upgrade():
>     	 	   op.drop_column('tea_profiles', 'price')
>
>           def downgrade():
>     		    op.add_column('tea_profiles', sa.Column('price', sa.Numeric(7, 2), nullable=True))
>
>    5. Set the DB URL in the terminal for the appropriate environment. For example, you would do this 
>       if you wanted to apply the migration to the local database:
>
>           $env:DATABASE_URL="postgresql://postgres:<local-password>@localhost:5432/<db-name>" 
>
>    6. Once you're sure the migration file is correct, apply the migration with
>
>     	    alembic upgrade head
>
>       This step will be performed automatically in all CD workflows.
>
>       Note that if you added a new field to an existing table with a default field, alembic will not 
>       add the field with "server_default" and the upgrade will fail.  You'll have to change the 
>       migration file manually like this:
>
>           op.add_column(
>               'users',
>               sa.Column(
>                   'is_verified',
>                   sa.Boolean(),
>                   server_default=sa.text('false'),
>                   nullable=False
>               )
>           )
>
>    7. Refresh the table in pgAdmin and confirm the change is applied.
