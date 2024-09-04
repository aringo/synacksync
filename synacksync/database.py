"""
database.py

This module provides functions to set up and manage a SQLite database used to store 
information about tasks, targets, and patch verifications. It includes functions to 
create tables, insert or update records, delete records, and fetch upcoming entries 
from the database.

Functions:
    setup_database(db_path: str) -> None:
        Creates the SQLite database at the specified path and initializes tables 
        for tasks, targets, and patch verifications if they do not already exist.

    save_targets_to_db(db_path: str, data: list, delete: bool = False) -> None:
        Inserts or updates records in the 'targets' table, or deletes records if 
        the delete flag is set to True.

    save_tasks_to_db(db_path: str, data: list, delete: bool = False) -> None:
        Inserts or updates records in the 'tasks' table, or deletes records if 
        the delete flag is set to True.

    save_patch_verifications_to_db(db_path: str, data: list, delete: bool = False) -> None:
        Inserts or updates records in the 'patch_verifications' table, or deletes 
        records if the delete flag is set to True.

    dict_factory(cursor: sqlite3.Cursor, row: tuple) -> dict:
        Converts SQLite query rows into dictionaries, mapping column names to 
        their respective values.

    get_upcoming_entries(db_path: str) -> tuple:
        Fetches upcoming tasks, targets, and patch verifications from the database 
        based on their respective timestamps and returns them as dictionaries.
"""

import sqlite3
import os
import datetime

def setup_database(db_path):
    if not os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS targets (
                id TEXT PRIMARY KEY,  -- Store the id value from the API
                category TEXT,
                codename TEXT,
                average_payout REAL,
                is_active BOOLEAN,
                start TIMESTAMP,
                discovery BOOLEAN,
                vuln_accepted INTEGER,
                dynamic_payment_percentage REAL,
                event_id TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                title TEXT,
                description TEXT,
                listing_codename TEXT,
                time_given INTEGER,
                claimed_on TIMESTAMP,
                max_completion_time TIMESTAMP,
                payout_amount REAL,  -- New field for payout amount
                payout_currency TEXT,  -- New field for payout currency
                event_id TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS patch_verifications (
                id TEXT PRIMARY KEY,
                message TEXT,
                expires TIMESTAMP,
                vuln_id TEXT,
                vuln_title TEXT,
                event_id TEXT
            )
        ''')
        
        conn.commit()
        conn.close()

def save_targets_to_db(db_path, data, delete=False):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    for item in data:
        if delete:
            cursor.execute('DELETE FROM targets WHERE id = ?', (item['id'],))
        else:
            cursor.execute('''
                INSERT OR REPLACE INTO targets (
                    id, category, codename, average_payout, is_active, start, discovery, vuln_accepted, dynamic_payment_percentage, event_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                item['id'], item['category'], item['codename'], item['averagePayout'], item['isActive'],
                item['start'], item['discovery'], item['vuln_accepted'], item['dynamic_payment_percentage'], item.get('event_id')
            ))
    
    conn.commit()
    conn.close()

def save_tasks_to_db(db_path, data, delete=False):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    for item in data:
        if delete:
            cursor.execute('DELETE FROM tasks WHERE id = ?', (item['id'],))
        else:
            cursor.execute('''
                INSERT OR REPLACE INTO tasks (
                    id, title, description, listing_codename, time_given, claimed_on, max_completion_time,
                    payout_amount, payout_currency, event_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                item['id'], item['title'], item['description'], item['listing_codename'],
                item['time_given'], item['claimed_on'], item['max_completion_time'],
                item['payout_amount'], item['payout_currency'], item.get('event_id')
            ))
    
    conn.commit()
    conn.close()

def save_patch_verifications_to_db(db_path, data, delete=False):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    for item in data:
        if delete:
            cursor.execute('DELETE FROM patch_verifications WHERE id = ?', (item['id'],))
        else:
            cursor.execute('''
                INSERT OR REPLACE INTO patch_verifications (
                    id, message, expires, vuln_id, vuln_title, event_id
                ) VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                item['id'], item['message'], item['expires'],
                item['vuln_id'], item['vuln_title'], item.get('event_id')
            ))
    
    conn.commit()
    conn.close()

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

def get_upcoming_entries(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = dict_factory
    cursor = conn.cursor()
    
    #  query for getting tasks, targets, and patch_verifications to check 
    cursor.execute("SELECT id, title, description, listing_codename, time_given, claimed_on, max_completion_time, payout_amount, payout_currency, event_id FROM tasks WHERE max_completion_time > ?", (datetime.datetime.now().timestamp(),))
    db_tasks = cursor.fetchall()

    cursor.execute("SELECT id, category, codename, average_payout as averagePayout, is_active as isActive, start, discovery, vuln_accepted, dynamic_payment_percentage, event_id FROM targets WHERE start > ?", (datetime.datetime.now().timestamp(),))
    db_targets = cursor.fetchall()

    cursor.execute("SELECT id, message, expires, vuln_id, vuln_title, event_id FROM patch_verifications WHERE expires > ?", (datetime.datetime.now().timestamp(),))
    db_patch_verifications = cursor.fetchall()

    conn.close()
    return db_tasks, db_targets, db_patch_verifications
