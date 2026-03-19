INSERT INTO teams (team_id, team_name) VALUES
    (1, 'マルチ業務1課'),
    (2, 'マルチ業務2課')
ON CONFLICT DO NOTHING;

INSERT INTO users (user_id, display_name, email, role, team_id, is_active) VALUES
    (1, '山田SV', 'yamada@example.com', 'sv', 1, TRUE),
    (2, '佐藤SV', 'sato@example.com', 'sv', 1, TRUE),
    (3, '田中SV', 'tanaka@example.com', 'sv', 2, TRUE),
    (4, '管理者', 'admin@example.com', 'admin', 1, TRUE)
ON CONFLICT DO NOTHING;

INSERT INTO projects (project_id, project_name, team_id) VALUES
    (1, 'LEOC', 1),
    (2, '入電管理', 1),
    (3, '品質監査', 2)
ON CONFLICT DO NOTHING;

INSERT INTO app_registry (app_id, app_key, app_name, description, display_order) VALUES
    (1, 'tasks', 'タスク', 'タスク管理', 1),
    (2, 'requests', 'SV依頼', 'SV依頼管理', 2),
    (3, 'leoc', 'LEOC速報', 'LEOC応答率速報', 3),
    (4, 'reports', '日報送信', '日報支援プレースホルダ', 4),
    (5, 'call_details', '呼詳細作成', '呼詳細支援プレースホルダ', 5)
ON CONFLICT DO NOTHING;
