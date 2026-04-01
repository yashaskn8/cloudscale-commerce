# ==============================================================================
# Root Variables — CloudScale Commerce Production Infrastructure
# ==============================================================================

variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Deployment environment (dev, staging, production)"
  type        = string
  default     = "production"
}

variable "project_name" {
  description = "Project identifier used for naming and tagging"
  type        = string
  default     = "cloudscale"
}

# ── Networking ─────────────────────────────────────────────────────────────────

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "List of AZs to distribute resources across"
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b", "us-east-1c"]
}

# ── EKS ────────────────────────────────────────────────────────────────────────

variable "eks_cluster_version" {
  description = "Kubernetes version for the EKS cluster"
  type        = string
  default     = "1.28"
}

variable "eks_node_instance_types" {
  description = "Instance types for EKS managed node group"
  type        = list(string)
  default     = ["m6i.large", "m6i.xlarge"]
}

variable "eks_node_desired_size" {
  description = "Desired number of EKS worker nodes"
  type        = number
  default     = 3
}

variable "eks_node_min_size" {
  description = "Minimum number of EKS worker nodes"
  type        = number
  default     = 2
}

variable "eks_node_max_size" {
  description = "Maximum number of EKS worker nodes"
  type        = number
  default     = 10
}

# ── RDS ────────────────────────────────────────────────────────────────────────

variable "rds_instance_class" {
  description = "RDS PostgreSQL instance class"
  type        = string
  default     = "db.r6g.large"
}

variable "rds_engine_version" {
  description = "PostgreSQL engine version"
  type        = string
  default     = "15.4"
}

variable "rds_allocated_storage" {
  description = "Initial storage allocation in GB"
  type        = number
  default     = 100
}

variable "rds_max_allocated_storage" {
  description = "Maximum autoscaling storage in GB"
  type        = number
  default     = 500
}

variable "rds_database_name" {
  description = "Default database name"
  type        = string
  default     = "cloudscale"
}

variable "rds_read_replica_count" {
  description = "Number of RDS read replicas"
  type        = number
  default     = 2
}

# ── ElastiCache ────────────────────────────────────────────────────────────────

variable "redis_node_type" {
  description = "ElastiCache Redis node type"
  type        = string
  default     = "cache.r6g.large"
}

variable "redis_num_cache_clusters" {
  description = "Number of cache nodes in the replication group"
  type        = number
  default     = 3
}

# ── MSK ────────────────────────────────────────────────────────────────────────

variable "msk_broker_instance_type" {
  description = "MSK Kafka broker instance type"
  type        = string
  default     = "kafka.m5.large"
}

variable "msk_broker_count" {
  description = "Number of MSK broker nodes"
  type        = number
  default     = 3
}

variable "msk_ebs_volume_size" {
  description = "EBS volume size per broker in GB"
  type        = number
  default     = 100
}

# ── DNS ────────────────────────────────────────────────────────────────────────

variable "domain_name" {
  description = "Primary domain name for the platform"
  type        = string
  default     = "cloudscale.io"
}
