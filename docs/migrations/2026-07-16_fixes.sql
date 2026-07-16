-- Миграция исправлений по ревью (2026-07-16). Применять на существующей прод-БД.
-- На свежей БД таблицы создаёт create_all (admin) — миграция не нужна.

ALTER TABLE objects ALTER COLUMN object_name DROP NOT NULL;
ALTER TABLE objects ADD COLUMN IF NOT EXISTS cancelled BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE consent_log ALTER COLUMN user_id DROP NOT NULL;
ALTER TABLE consent_log ADD COLUMN IF NOT EXISTS telegram_id BIGINT;
ALTER TABLE cached_files ADD COLUMN IF NOT EXISTS file_mtime DOUBLE PRECISION;
UPDATE legal_documents SET file_path = replace(file_path, '/uploads/', '/app/uploads/')
  WHERE file_path LIKE '/uploads/%';
UPDATE mailings SET status = 'pending' WHERE status = 'sending';

-- Перед заменой контента на реальный (Фаза 3), чтобы кэш file_id перезалился:
DELETE FROM cached_files;
