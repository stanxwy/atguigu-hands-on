-- =============================================================================
-- 自动化安全评估系统 — 数据库与账号初始化脚本
-- 说明：仅负责「库 + 账号」层，不含业务 DDL。
--       业务表结构由 Alembic 迁移或 scripts/init_db.py（create_all）管理。
-- 执行：mysql -uroot -p < db/init.sql
-- =============================================================================

CREATE DATABASE IF NOT EXISTS code_sec_evaluator
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

-- 应用账号（生产环境请务必修改密码，且避免使用弱口令）
CREATE USER IF NOT EXISTS 'cse_user'@'%' IDENTIFIED BY 'cse_password_change_me';

GRANT ALL PRIVILEGES ON code_sec_evaluator.* TO 'cse_user'@'%';

FLUSH PRIVILEGES;
