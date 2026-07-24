# ==============================================================================
# RDS Module — High Performance PostgreSQL Primary + Read Replica Cluster
# Features Multi-AZ primary deployment, encrypted disks, and custom parameter groups.
# ==============================================================================

variable "project_name" {
  type = string
}

variable "environment" {
  type = string
}

variable "vpc_id" {
  type = string
}

variable "private_subnet_ids" {
  type = list(string)
}

variable "instance_class" {
  type = string
}

variable "engine_version" {
  type = string
}

variable "allocated_storage" {
  type = number
}

variable "max_allocated_storage" {
  type = number
}

variable "database_name" {
  type = string
}

variable "read_replica_count" {
  type = number
}

variable "kms_key_arn" {
  type = string
}

variable "eks_security_group_id" {
  type = string
}

# ── DB Subnet Group ────────────────────────────────────────────────────────────

resource "aws_db_subnet_group" "main" {
  name       = "${var.project_name}-${var.environment}-rds-subnet-group"
  subnet_ids = var.private_subnet_ids

  tags = {
    Name = "${var.project_name}-${var.environment}-rds-subnet-group"
  }
}

# ── Security Group ─────────────────────────────────────────────────────────────

resource "aws_security_group" "rds" {
  name        = "${var.project_name}-${var.environment}-rds-sg"
  description = "Security group for PostgreSQL RDS instances"
  vpc_id      = var.vpc_id

  ingress {
    description     = "PostgreSQL from EKS Nodes"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [var.eks_security_group_id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-rds-sg"
  }
}

# ── Parameter Group ────────────────────────────────────────────────────────────

resource "aws_db_parameter_group" "main" {
  name   = "${var.project_name}-${var.environment}-pg"
  family = "postgres15"

  parameter {
    name  = "rds.force_ssl"
    value = "1"
  }

  parameter {
    name  = "max_connections"
    value = "500"
  }

  parameter {
    name  = "shared_buffers"
    value = "{DBInstanceClassMemory/32768}" # Dynamic memory allocation
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-rds-params"
  }
}

# ── Primary Database Instance (Multi-AZ Write Core) ──────────────────────────

resource "aws_db_instance" "primary" {
  identifier                  = "${var.project_name}-${var.environment}-rds-primary"
  engine                      = "postgres"
  engine_version              = var.engine_version
  instance_class              = var.instance_class
  allocated_storage           = var.allocated_storage
  max_allocated_storage       = var.max_allocated_storage
  storage_type                = "gp3"
  db_name                     = var.database_name
  username                    = "cloudscale_admin"
  password                    = "SuperSecurePassword123!" # Should be rotated via secrets manager

  db_subnet_group_name        = aws_db_subnet_group.main.name
  vpc_security_group_ids      = [aws_security_group.rds.id]
  parameter_group_name        = aws_db_parameter_group.main.name
  
  multi_az                    = true
  publicly_accessible         = false
  storage_encrypted           = true
  kms_key_id                  = var.kms_key_arn

  backup_retention_period     = 7
  backup_window               = "03:00-04:00"
  maintenance_window          = "sun:04:30-sun:05:30"
  copy_tags_to_snapshot       = true
  deletion_protection         = false # Set to true for production systems
  skip_final_snapshot         = true

  tags = {
    Name = "${var.project_name}-${var.environment}-db-primary"
  }
}

# ── Read Replicas (Distributed Queries Offloading) ────────────────────────────

resource "aws_db_instance" "replica" {
  count                       = var.read_replica_count
  identifier                  = "${var.project_name}-${var.environment}-rds-replica-${count.index}"
  
  replicate_source_db         = aws_db_instance.primary.identifier
  instance_class              = var.instance_class
  storage_type                = "gp3"
  publicly_accessible         = false
  vpc_security_group_ids      = [aws_security_group.rds.id]
  parameter_group_name        = aws_db_parameter_group.main.name

  storage_encrypted           = true
  kms_key_id                  = var.kms_key_arn
  skip_final_snapshot         = true

  tags = {
    Name = "${var.project_name}-${var.environment}-db-replica-${count.index}"
  }
}

# ── Outputs ────────────────────────────────────────────────────────────────────

output "primary_instance_id" {
  value = aws_db_instance.primary.id
}

output "primary_endpoint" {
  value = aws_db_instance.primary.endpoint
}

output "reader_endpoint" {
  value = length(aws_db_instance.replica) > 0 ? aws_db_instance.replica[0].endpoint : aws_db_instance.primary.endpoint
}
