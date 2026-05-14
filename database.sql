-- ==============================================================================
-- Plant Doctor AI — Database Schema (SQL Server)
-- ==============================================================================

-- Database banao (agar nahi hai)
IF NOT EXISTS (SELECT * FROM sys.databases WHERE name = 'PlantDoctor')
    CREATE DATABASE PlantDoctor;
GO

USE PlantDoctor;
GO

-- ==============================================================================
-- 1. Users Table
-- ==============================================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='users' AND xtype='U')
CREATE TABLE users (
    id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
    full_name NVARCHAR(100) NOT NULL,
    email NVARCHAR(100) UNIQUE NOT NULL,
    phone NVARCHAR(20),
    password_hash NVARCHAR(255) NOT NULL,
    role NVARCHAR(20) DEFAULT 'farmer',        -- farmer, expert, admin
    location NVARCHAR(100),
    is_active BIT DEFAULT 1,
    created_at DATETIME DEFAULT GETDATE()
);
GO

-- ==============================================================================
-- 2. Scan History Table
-- ==============================================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='scans' AND xtype='U')
CREATE TABLE scans (
    id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
    user_id UNIQUEIDENTIFIER,
    crop_type NVARCHAR(50),
    image_url NVARCHAR(500),
    predicted_disease NVARCHAR(100),
    confidence FLOAT,
    ai_advice NVARCHAR(MAX),
    created_at DATETIME DEFAULT GETDATE(),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
GO

-- ==============================================================================
-- 3. Expert Consultations Table
-- ==============================================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='consultations' AND xtype='U')
CREATE TABLE consultations (
    id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
    scan_id UNIQUEIDENTIFIER,
    farmer_id UNIQUEIDENTIFIER,
    expert_id UNIQUEIDENTIFIER NULL,
    status NVARCHAR(20) DEFAULT 'pending',      -- pending, active, resolved
    message NVARCHAR(MAX),
    expert_reply NVARCHAR(MAX) NULL,
    created_at DATETIME DEFAULT GETDATE(),
    resolved_at DATETIME NULL,
    FOREIGN KEY (scan_id) REFERENCES scans(id),
    FOREIGN KEY (farmer_id) REFERENCES users(id),
    FOREIGN KEY (expert_id) REFERENCES users(id)
);
GO

-- ==============================================================================
-- 4. Disease Knowledge Base
-- ==============================================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='diseases' AND xtype='U')
CREATE TABLE diseases (
    id INT IDENTITY(1,1) PRIMARY KEY,
    crop NVARCHAR(50),
    disease_name NVARCHAR(100),
    symptoms NVARCHAR(MAX),
    causes NVARCHAR(MAX),
    chemical_treatment NVARCHAR(MAX),
    organic_treatment NVARCHAR(MAX),
    prevention NVARCHAR(MAX),
    severity_level INT DEFAULT 3               -- 1=Low, 5=Critical
);
GO

-- ==============================================================================
-- Indexes for Performance
-- ==============================================================================
CREATE INDEX IX_scans_user_id ON scans(user_id);
CREATE INDEX IX_scans_created_at ON scans(created_at DESC);
CREATE INDEX IX_consultations_status ON consultations(status);
CREATE INDEX IX_users_email ON users(email);
GO

-- ==============================================================================
-- Verify
-- ==============================================================================
SELECT 'users' as [Table], COUNT(*) as [Rows] FROM users
UNION ALL
SELECT 'scans', COUNT(*) FROM scans
UNION ALL
SELECT 'consultations', COUNT(*) FROM consultations
UNION ALL
SELECT 'diseases', COUNT(*) FROM diseases;
GO 


UPDATE users SET role = 'admin' WHERE email = 'Khan98saqlain@gmail.com';
select * from users 
