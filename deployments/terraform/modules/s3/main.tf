# ==============================================================================
# S3 Module — Secure, Encrypted, Versioned Object Storage Buckets
# Provisions buckets for invoices, backups, log data, and static assets.
# ==============================================================================

variable "project_name" {
  type = string
}

variable "environment" {
  type = string
}

variable "kms_key_arn" {
  type = string
}

# ── 1. Invoices Bucket ─────────────────────────────────────────────────────────

resource "aws_s3_bucket" "invoices" {
  bucket        = "${var.project_name}-${var.environment}-invoices"
  force_destroy = false
}

resource "aws_s3_bucket_versioning" "invoices" {
  bucket = aws_s3_bucket.invoices.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "invoices" {
  bucket = aws_s3_bucket.invoices.id
  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = var.kms_key_arn
      sse_algorithm     = "aws:kms"
    }
  }
}

# ── 2. Backups Bucket ──────────────────────────────────────────────────────────

resource "aws_s3_bucket" "backups" {
  bucket        = "${var.project_name}-${var.environment}-backups"
  force_destroy = false
}

resource "aws_s3_bucket_server_side_encryption_configuration" "backups" {
  bucket = aws_s3_bucket.backups.id
  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = var.kms_key_arn
      sse_algorithm     = "aws:kms"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "backups" {
  bucket = aws_s3_bucket.backups.id

  rule {
    id     = "expire_old_backups"
    status = "Enabled"

    transition {
      days          = 30
      storage_class = "GLACIER"
    }

    expiration {
      days = 90
    }
  }
}

# ── 3. Application Logs Bucket ──────────────────────────────────────────────────

resource "aws_s3_bucket" "logs" {
  bucket        = "${var.project_name}-${var.environment}-application-logs"
  force_destroy = false
}

resource "aws_s3_bucket_lifecycle_configuration" "logs" {
  bucket = aws_s3_bucket.logs.id

  rule {
    id     = "archive_logs"
    status = "Enabled"

    transition {
      days          = 14
      storage_class = "GLACIER"
    }

    expiration {
      days = 365
    }
  }
}

# ── S3 Public Access Block (Secure by Default) ──────────────────────────────────

resource "aws_s3_bucket_public_access_block" "block_invoices" {
  bucket                  = aws_s3_bucket.invoices.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_public_access_block" "block_backups" {
  bucket                  = aws_s3_bucket.backups.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_public_access_block" "block_logs" {
  bucket                  = aws_s3_bucket.logs.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# ── Outputs ────────────────────────────────────────────────────────────────────

output "invoices_bucket_id" {
  value = aws_s3_bucket.invoices.id
}

output "backups_bucket_id" {
  value = aws_s3_bucket.backups.id
}

output "logs_bucket_id" {
  value = aws_s3_bucket.logs.id
}
