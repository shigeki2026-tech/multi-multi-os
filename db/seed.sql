INSERT INTO teams (team_id, team_name, created_at, updated_at) VALUES
    (1, 'マルチ業務1課', NOW(), NOW()),
    (2, 'マルチ業務2課', NOW(), NOW());

INSERT INTO users (user_id, google_email, display_name, email, role, team_id, is_active, last_login_at, created_at, updated_at) VALUES
    (1, 'ohama@example.com', '大濱成基', 'ohama@example.com', 'admin', 1, TRUE, NULL, NOW(), NOW()),
    (2, 'yamada@example.com', '山田SV', 'yamada@example.com', 'sv', 1, TRUE, NULL, NOW(), NOW()),
    (3, 'sato@example.com', '佐藤SV', 'sato@example.com', 'sv', 1, TRUE, NULL, NOW(), NOW()),
    (4, 'tanaka@example.com', '田中SV', 'tanaka@example.com', 'sv', 2, TRUE, NULL, NOW(), NOW());

INSERT INTO projects (project_id, project_name, team_id, color, display_order, is_active, created_at, updated_at) VALUES
    (1, '代表案件A', 1, '#4F8CFF', 10, TRUE, NOW(), NOW()),
    (2, '受電一次対応', 1, '#34C759', 20, TRUE, NOW(), NOW()),
    (3, '品質確認', 2, '#FF9F0A', 30, TRUE, NOW(), NOW());

INSERT INTO tasks (
    task_id, task_type, title, description, requester_user_id, assignee_user_id, team_id, project_id,
    priority, status, due_date, requested_date, needs_confirmation, related_link, is_active, deleted_at, deleted_by,
    created_at, updated_at
) VALUES
    (1, 'personal_task', '午前中の件数チェック', '当日件数の確認', 1, 2, 1, 1, '高', '進行中', CURRENT_DATE, NULL, FALSE, NULL, TRUE, NULL, NULL, NOW(), NOW()),
    (2, 'team_task', '引継ぎ内容の整理', '夕会向けの引継ぎ事項を整理', 2, 3, 1, 2, '中', '未着手', CURRENT_DATE, NULL, FALSE, NULL, TRUE, NULL, NULL, NOW(), NOW()),
    (3, 'handover_task', '前日未処理の確認', '未処理案件の有無を確認', 3, 2, 1, 3, '高', '確認待ち', CURRENT_DATE - INTERVAL '1 day', NULL, TRUE, NULL, TRUE, NULL, NULL, NOW(), NOW()),
    (4, 'sv_request', '14時速報の作成', '14:00時点の速報を作成してください', 3, 2, 1, 1, '高', '確認待ち', CURRENT_DATE, CURRENT_DATE, TRUE, 'https://example.local/summary', TRUE, NULL, NULL, NOW(), NOW());

INSERT INTO leoc_snapshots (
    snapshot_id, snapshot_time, inbound_count, lost_count, answer_rate, ai_count, form_count,
    source_type, source_ref, created_by, created_at
) VALUES
    (1, '13:00', 6, 2, 75.0, 4, 6, 'seed', 'sample', 2, NOW());

INSERT INTO app_registry (app_id, app_key, app_name, description, display_order, is_enabled, created_at, updated_at) VALUES
    (1, 'tasks', 'タスク', 'タスク管理', 1, TRUE, NOW(), NOW()),
    (2, 'requests', 'SV依頼', 'SV依頼管理', 2, TRUE, NOW(), NOW()),
    (3, 'leoc', '応答率速報', '応答率速報', 3, TRUE, NOW(), NOW()),
    (4, 'reports', '日報送信', '日報送信', 4, TRUE, NOW(), NOW()),
    (5, 'call_details', '呼詳細作成', '呼詳細作成', 5, TRUE, NOW(), NOW());
