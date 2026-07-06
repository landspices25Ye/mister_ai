-- =================================================================
-- Mister AI - PostgreSQL Schema (DDL)
-- الإصدار: 1.0
-- التاريخ: 2026-07-05
-- الاستخدام: psql -U user -d mister_ai -f schema.sql
-- =================================================================

-- تفعيل الإضافات المطلوبة
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";      -- UUID generation
CREATE EXTENSION IF NOT EXISTS "pg_trgm";        -- للبحث النصي السريع
CREATE EXTENSION IF NOT EXISTS "vector";         -- للـ embeddings (pgvector)
-- ملاحظة: إذا لم تستخدم pgvector، احذف السطر أعلاه واستخدم Qdrant منفصل

-- =================================================================
-- 1. الطلاب
-- =================================================================
CREATE TABLE students (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    telegram_id BIGINT UNIQUE,
    whatsapp_phone VARCHAR(20) UNIQUE,
    name VARCHAR(100) NOT NULL,
    grade VARCHAR(50) NOT NULL,  -- "third_secondary_science"
    preferred_language VARCHAR(10) DEFAULT 'ar',
    joined_at TIMESTAMPTZ DEFAULT NOW(),
    last_active_at TIMESTAMPTZ,
    total_messages INT DEFAULT 0,
    metadata JSONB DEFAULT '{}'::jsonb,
    is_active BOOLEAN DEFAULT TRUE,
    consent_given BOOLEAN DEFAULT FALSE,  -- موافقة الأهل للقاصرين
    consent_date TIMESTAMPTZ
);

CREATE INDEX idx_students_telegram ON students(telegram_id) WHERE telegram_id IS NOT NULL;
CREATE INDEX idx_students_whatsapp ON students(whatsapp_phone) WHERE whatsapp_phone IS NOT NULL;
CREATE INDEX idx_students_grade ON students(grade);
CREATE INDEX idx_students_active ON students(is_active, last_active_at);

-- =================================================================
-- 2. الفصول والدروس
-- =================================================================
CREATE TABLE chapters (
    id VARCHAR(50) PRIMARY KEY,  -- "ch01_derivatives"
    subject_id VARCHAR(50) NOT NULL,  -- "math", "physics"
    grade VARCHAR(50) NOT NULL,  -- "third_secondary_science"
    title_ar VARCHAR(200) NOT NULL,
    title_en VARCHAR(200),
    order_index INT NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE lessons (
    id VARCHAR(50) PRIMARY KEY,  -- "lesson_1_1"
    chapter_id VARCHAR(50) NOT NULL REFERENCES chapters(id) ON DELETE CASCADE,
    title_ar VARCHAR(200) NOT NULL,
    title_en VARCHAR(200),
    content_markdown TEXT NOT NULL,
    summary TEXT,
    difficulty_level INT DEFAULT 1 CHECK (difficulty_level BETWEEN 1 AND 5),
    estimated_minutes INT DEFAULT 45,
    order_index INT NOT NULL,
    keywords TEXT[],  -- للبحث
    learning_objectives TEXT[],
    prerequisites TEXT[],
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_lessons_chapter ON lessons(chapter_id, order_index);
CREATE INDEX idx_lessons_keywords ON lessons USING GIN(keywords);

-- =================================================================
-- 3. بنك الأسئلة
-- =================================================================
CREATE TABLE questions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    lesson_id VARCHAR(50) REFERENCES lessons(id) ON DELETE CASCADE,
    question_type VARCHAR(20) NOT NULL,  -- "mcq", "true_false", "fill_blank", "short_answer"
    difficulty_level INT DEFAULT 1 CHECK (difficulty_level BETWEEN 1 AND 5),
    question_text TEXT NOT NULL,
    options JSONB,  -- للـ MCQ: [{"id": "a", "text": "..."}, ...]
    correct_answer TEXT NOT NULL,
    explanation TEXT,
    hints TEXT[],
    points INT DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_questions_lesson ON questions(lesson_id);
CREATE INDEX idx_questions_type ON questions(question_type, difficulty_level);

-- =================================================================
-- 4. الجلسات
-- =================================================================
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    student_id UUID NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    ended_at TIMESTAMPTZ,
    message_count INT DEFAULT 0,
    session_metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_sessions_student ON sessions(student_id, started_at DESC);
CREATE INDEX idx_sessions_active ON sessions(student_id) WHERE ended_at IS NULL;

-- =================================================================
-- 5. الرسائل
-- =================================================================
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    student_id UUID NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    retrieved_lesson_ids TEXT[],  -- IDs الدروس المسترجعة من RAG
    llm_model VARCHAR(50),  -- "gpt-4o-mini", "claude-3-haiku", etc.
    tokens_input INT,
    tokens_output INT,
    latency_ms INT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_messages_session ON messages(session_id, created_at);
CREATE INDEX idx_messages_student ON messages(student_id, created_at DESC);

-- =================================================================
-- 6. تقدّم الطالب
-- =================================================================
CREATE TABLE student_progress (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    student_id UUID NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    lesson_id VARCHAR(50) NOT NULL REFERENCES lessons(id) ON DELETE CASCADE,
    mastery_status VARCHAR(20) DEFAULT 'not_started'
        CHECK (mastery_status IN ('not_started', 'learning', 'practicing', 'mastered')),
    last_quiz_score DECIMAL(5,2),  -- 0-100
    best_quiz_score DECIMAL(5,2),
    attempts_count INT DEFAULT 0,
    time_spent_minutes INT DEFAULT 0,
    weak_topics TEXT[],
    last_attempt_at TIMESTAMPTZ,
    mastered_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(student_id, lesson_id)
);

CREATE INDEX idx_progress_student ON student_progress(student_id);
CREATE INDEX idx_progress_status ON student_progress(mastery_status);
CREATE INDEX idx_progress_lesson ON student_progress(lesson_id, mastery_status);

-- =================================================================
-- 7. نتائج الاختبارات
-- =================================================================
CREATE TABLE quiz_attempts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    student_id UUID NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    lesson_id VARCHAR(50) NOT NULL REFERENCES lessons(id) ON DELETE CASCADE,
    score DECIMAL(5,2) NOT NULL,  -- 0-100
    total_questions INT NOT NULL,
    correct_answers INT NOT NULL,
    time_taken_seconds INT,
    answers JSONB,  -- [{"question_id": "...", "answer": "...", "correct": true}, ...]
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_quiz_student ON quiz_attempts(student_id, completed_at DESC);
CREATE INDEX idx_quiz_lesson ON quiz_attempts(lesson_id);

-- =================================================================
-- 8. Vector Embeddings (إذا استخدمت pgvector بدل Qdrant)
-- =================================================================
-- إذا كنت تستخدم Qdrant منفصل، احذف هذا القسم بالكامل
CREATE TABLE IF NOT EXISTS lesson_chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    lesson_id VARCHAR(50) NOT NULL REFERENCES lessons(id) ON DELETE CASCADE,
    chunk_index INT NOT NULL,
    chunk_text TEXT NOT NULL,
    embedding vector(1536),  -- بُعد OpenAI embeddings
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_chunks_lesson ON lesson_chunks(lesson_id);
CREATE INDEX idx_chunks_embedding ON lesson_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- =================================================================
-- 9. سجل العمليات (Audit Log)
-- =================================================================
CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    actor_type VARCHAR(20) NOT NULL,  -- "student", "admin", "system"
    actor_id UUID,
    action VARCHAR(50) NOT NULL,  -- "login", "message_sent", "consent_given", etc.
    target_type VARCHAR(50),
    target_id UUID,
    details JSONB,
    ip_address INET,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_audit_actor ON audit_log(actor_id, created_at DESC);
CREATE INDEX idx_audit_action ON audit_log(action, created_at DESC);

-- =================================================================
-- 10. ملاحظات المعلم البشري (للمراجعة)
-- =================================================================
CREATE TABLE human_reviews (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    message_id UUID REFERENCES messages(id) ON DELETE CASCADE,
    reviewer_id VARCHAR(50),  -- معرّف المراجع
    rating INT CHECK (rating BETWEEN 1 AND 5),
    feedback TEXT,
    suggested_answer TEXT,
    reviewed_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_reviews_message ON human_reviews(message_id);
CREATE INDEX idx_reviews_reviewer ON human_reviews(reviewer_id);

-- =================================================================
-- Views (عرض مفيد)
-- =================================================================

-- ملخص نشاط الطالب
CREATE OR REPLACE VIEW student_activity_summary AS
SELECT
    s.id,
    s.name,
    s.grade,
    s.joined_at,
    s.last_active_at,
    s.total_messages,
    COUNT(DISTINCT ses.id) AS total_sessions,
    COUNT(DISTINCT sp.lesson_id) AS lessons_touched,
    COUNT(DISTINCT CASE WHEN sp.mastery_status = 'mastered' THEN sp.lesson_id END) AS lessons_mastered,
    MAX(ses.started_at) AS last_session_at
FROM students s
LEFT JOIN sessions ses ON ses.student_id = s.id
LEFT JOIN student_progress sp ON sp.student_id = s.id
GROUP BY s.id;

-- الدروس الأكثر طلباً
CREATE OR REPLACE VIEW popular_lessons AS
SELECT
    l.id,
    l.title_ar,
    l.chapter_id,
    COUNT(m.id) AS retrieval_count
FROM lessons l
LEFT JOIN messages m ON l.id = ANY(string_to_array(m.retrieved_lesson_ids[1], ',')::text[])
GROUP BY l.id, l.title_ar, l.chapter_id
ORDER BY retrieval_count DESC;

-- =================================================================
-- Seed Data - البيانات الأولية
-- =================================================================

-- إدراج الفصول (استخدمها مرة واحدة)
INSERT INTO chapters (id, subject_id, grade, title_ar, title_en, order_index, description) VALUES
('ch01_derivatives', 'math', 'third_secondary_science', 'حساب التفاضل', 'Differentiation', 1, 'الاشتقاق وتطبيقاته الأساسية'),
('ch02_applications', 'math', 'third_secondary_science', 'تطبيقات التفاضل', 'Applications of Differentiation', 2, 'المعدلات المرتبطة والقيم القصوى'),
('ch03_integration', 'math', 'third_secondary_science', 'التكامل غير المحدود', 'Indefinite Integration', 3, 'مفهوم التكامل والقواعد الأساسية'),
('ch04_applications_integration', 'math', 'third_secondary_science', 'التكامل المحدود', 'Definite Integration', 4, 'المساحات والحجوم'),
('ch05_matrices', 'math', 'third_secondary_science', 'المصفوفات', 'Matrices', 5, 'العمليات على المصفوفات'),
('ch06_determinants', 'math', 'third_secondary_science', 'المحددات', 'Determinants', 6, 'حساب المحددات وخصائصها'),
('ch07_linear_systems', 'math', 'third_secondary_science', 'حل المعادلات الخطية', 'Linear Systems', 7, 'كرامر وجاوس والمصفوفات المعكوسة'),
('ch08_vectors', 'math', 'third_secondary_science', 'المتجهات في الفراغ', '3D Vectors', 8, 'العمليات على المتجهات والضرب القياسي والاتجاهي'),
('ch09_solid_geometry', 'math', 'third_secondary_science', 'الهندسة الفراغية', 'Solid Geometry', 9, 'المستقيمات والمستويات والأجسام الدورانية'),
('ch10_probability', 'math', 'third_secondary_science', 'الاحتمالات', 'Probability', 10, 'التوزيعات الاحتمالية'),
('ch11_statistics', 'math', 'third_secondary_science', 'الإحصاء', 'Statistics', 11, 'التقدير واختبار الفرضيات'),
('ch12_sequences_series', 'math', 'third_secondary_science', 'المتتاليات والمتسلسلات', 'Sequences and Series', 12, 'الحسابية والهندسية')
ON CONFLICT (id) DO NOTHING;

-- =================================================================
-- المستخدم الإداري (لوحة التحكم)
-- =================================================================
-- في الإنتاج، استخدم نظام auth كامل. هذا مثال فقط.
CREATE TABLE admin_users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(200) UNIQUE NOT NULL,
    password_hash VARCHAR(200) NOT NULL,  -- bcrypt
    name VARCHAR(100),
    role VARCHAR(20) DEFAULT 'reviewer',  -- "admin", "reviewer", "viewer"
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_login_at TIMESTAMPTZ
);

-- =================================================================
-- Functions & Triggers
-- =================================================================

-- تحديث total_messages تلقائياً
CREATE OR REPLACE FUNCTION update_student_message_count()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE students
    SET total_messages = total_messages + 1,
        last_active_at = NOW()
    WHERE id = NEW.student_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_message_count
AFTER INSERT ON messages
FOR EACH ROW
EXECUTE FUNCTION update_student_message_count();

-- تحديث session.message_count
CREATE OR REPLACE FUNCTION update_session_message_count()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE sessions
    SET message_count = message_count + 1
    WHERE id = NEW.session_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_session_count
AFTER INSERT ON messages
FOR EACH ROW
EXECUTE FUNCTION update_session_message_count();

-- =================================================================
-- ملاحظات للاستخدام
-- =================================================================
-- 1. شغّل هذا الملف: psql -U postgres -d mister_ai -f schema.sql
-- 2. تأكد من أن PostgreSQL 14+ (لدعم UUID و JSONB و pgvector)
-- 3. إذا لم تستخدم pgvector، احذف الـ extension والجدول lesson_chunks
-- 4. غيّر كلمات المرور الافتراضية قبل النشر
-- 5. شغّل pg_dump بانتظام للنسخ الاحتياطي
-- =================================================================
