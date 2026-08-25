-- 种子数据（故意埋点，仅供安全评估演示）
-- 漏洞：明文口令存储（敏感信息泄露），且均为弱口令
INSERT INTO users (username, password) VALUES
    ('admin', 'admin123'),
    ('alice', 'password1'),
    ('bob', 'qwerty123'),
    ('carol', '123456');
