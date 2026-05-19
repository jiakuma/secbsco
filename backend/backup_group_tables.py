"""
群组相关表数据备份脚本
执行方式：python backup_group_tables.py
"""
import os
import sys
from datetime import datetime

try:
    import pymysql
except ImportError:
    print("请先安装 pymysql: pip install pymysql")
    sys.exit(1)

DB_CONFIG = {
    'host': '127.0.0.1',
    'port': 3306,
    'user': 'root',
    'password': '123456',
    'database': 'biosecurity_stat',
    'charset': 'utf8mb4'
}

BACKUP_TABLES = [
    'group_info',
    'group_member',
    'group_node',
    'group_lifecycle_log',
    'sys_user_group',
]

def backup_tables():
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_dir = os.path.join(os.path.dirname(__file__), 'backups')
    os.makedirs(backup_dir, exist_ok=True)
    
    backup_file = os.path.join(backup_dir, f'group_backup_{timestamp}.sql')
    
    print(f"连接数据库: {DB_CONFIG['database']}")
    
    try:
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        with open(backup_file, 'w', encoding='utf-8') as f:
            f.write(f"-- 群组数据备份\n")
            f.write(f"-- 备份时间: {datetime.now()}\n")
            f.write(f"-- 数据库: {DB_CONFIG['database']}\n\n")
            
            for table in BACKUP_TABLES:
                print(f"备份表: {table}")
                
                cursor.execute(f"SHOW CREATE TABLE `{table}`")
                create_sql = cursor.fetchone()[1]
                f.write(f"-- 表结构: {table}\n")
                f.write(f"DROP TABLE IF EXISTS `{table}`;\n")
                f.write(f"{create_sql};\n\n")
                
                cursor.execute(f"SELECT COUNT(*) FROM `{table}`")
                count = cursor.fetchone()[0]
                print(f"  记录数: {count}")
                
                if count > 0:
                    cursor.execute(f"SELECT * FROM `{table}`")
                    rows = cursor.fetchall()
                    
                    cursor.execute(f"DESCRIBE `{table}`")
                    columns = [col[0] for col in cursor.fetchall()]
                    col_list = ', '.join([f'`{c}`' for c in columns])
                    
                    for row in rows:
                        values = []
                        for val in row:
                            if val is None:
                                values.append('NULL')
                            elif isinstance(val, str):
                                val_escaped = val.replace("'", "''")
                                values.append(f"'{val_escaped}'")
                            elif isinstance(val, datetime):
                                values.append(f"'{val.strftime('%Y-%m-%d %H:%M:%S')}'")
                            else:
                                values.append(str(val))
                        
                        val_list = ', '.join(values)
                        f.write(f"INSERT INTO `{table}` ({col_list}) VALUES ({val_list});\n")
                    
                    f.write("\n")
        
        cursor.close()
        conn.close()
        
        print(f"\n备份完成！")
        print(f"备份文件: {backup_file}")
        print(f"文件大小: {os.path.getsize(backup_file) / 1024:.2f} KB")
        
        return backup_file
        
    except Exception as e:
        print(f"备份失败: {e}")
        return None

if __name__ == '__main__':
    backup_tables()
