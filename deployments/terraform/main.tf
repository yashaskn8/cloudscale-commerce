# ==============================================================================
# Root Module — CloudScale Commerce Production Infrastructure
# Orchestrates all child modules in dependency order.
# ==============================================================================

module "vpc" {
  source = "./modules/vpc"

  project_name       = var.project_name
  environment        = var.environment
  vpc_cidr           = var.vpc_cidr
  availability_zones = var.availability_zones
}

module "security" {
  source = "./modules/security"

  project_name = var.project_name
  environment  = var.environment
  vpc_id       = module.vpc.vpc_id
}

module "eks" {
  source = "./modules/eks"

  project_name        = var.project_name
  environment         = var.environment
  cluster_version     = var.eks_cluster_version
  vpc_id              = module.vpc.vpc_id
  private_subnet_ids  = module.vpc.private_subnet_ids
  node_instance_types = var.eks_node_instance_types
  node_desired_size   = var.eks_node_desired_size
  node_min_size       = var.eks_node_min_size
  node_max_size       = var.eks_node_max_size
  kms_key_arn         = module.security.kms_key_arn
}

module "rds" {
  source = "./modules/rds"

  project_name          = var.project_name
  environment           = var.environment
  vpc_id                = module.vpc.vpc_id
  private_subnet_ids    = module.vpc.private_subnet_ids
  instance_class        = var.rds_instance_class
  engine_version        = var.rds_engine_version
  allocated_storage     = var.rds_allocated_storage
  max_allocated_storage = var.rds_max_allocated_storage
  database_name         = var.rds_database_name
  read_replica_count    = var.rds_read_replica_count
  kms_key_arn           = module.security.kms_key_arn
  eks_security_group_id = module.eks.node_security_group_id
}

module "elasticache" {
  source = "./modules/elasticache"

  project_name          = var.project_name
  environment           = var.environment
  vpc_id                = module.vpc.vpc_id
  private_subnet_ids    = module.vpc.private_subnet_ids
  node_type             = var.redis_node_type
  num_cache_clusters    = var.redis_num_cache_clusters
  kms_key_arn           = module.security.kms_key_arn
  eks_security_group_id = module.eks.node_security_group_id
}

module "msk" {
  source = "./modules/msk"

  project_name          = var.project_name
  environment           = var.environment
  vpc_id                = module.vpc.vpc_id
  private_subnet_ids    = module.vpc.private_subnet_ids
  broker_instance_type  = var.msk_broker_instance_type
  broker_count          = var.msk_broker_count
  ebs_volume_size       = var.msk_ebs_volume_size
  kms_key_arn           = module.security.kms_key_arn
  eks_security_group_id = module.eks.node_security_group_id
}

module "s3" {
  source = "./modules/s3"

  project_name = var.project_name
  environment  = var.environment
  kms_key_arn  = module.security.kms_key_arn
}

module "monitoring" {
  source = "./modules/monitoring"

  project_name   = var.project_name
  environment    = var.environment
  eks_cluster_id = module.eks.cluster_id
  rds_id         = module.rds.primary_instance_id
  redis_id       = module.elasticache.replication_group_id
  msk_cluster_arn = module.msk.cluster_arn
}
