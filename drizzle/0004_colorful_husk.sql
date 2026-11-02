CREATE TABLE `admin_audit_logs` (
	`id` int AUTO_INCREMENT NOT NULL,
	`actorId` int,
	`actorName` varchar(160) NOT NULL,
	`actorRole` varchar(60) NOT NULL,
	`action` varchar(80) NOT NULL,
	`targetName` varchar(160),
	`details` text,
	`ipAddress` varchar(80),
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	CONSTRAINT `admin_audit_logs_id` PRIMARY KEY(`id`)
);
--> statement-breakpoint
CREATE TABLE `admin_staff` (
	`id` int AUTO_INCREMENT NOT NULL,
	`userId` int,
	`username` varchar(120) NOT NULL,
	`displayName` varchar(160) NOT NULL,
	`passwordHash` varchar(255) NOT NULL,
	`roleKey` varchar(40) NOT NULL DEFAULT 'staff',
	`permissionsJson` text NOT NULL,
	`isActive` boolean NOT NULL DEFAULT true,
	`mustChangePassword` boolean NOT NULL DEFAULT true,
	`sessionVersion` int NOT NULL DEFAULT 1,
	`createdBy` varchar(160),
	`lastLoginAt` timestamp,
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	`updatedAt` timestamp NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
	CONSTRAINT `admin_staff_id` PRIMARY KEY(`id`),
	CONSTRAINT `admin_staff_username_unique` UNIQUE(`username`),
	CONSTRAINT `admin_staff_username_uq` UNIQUE(`username`)
);
--> statement-breakpoint
CREATE TABLE `order_number_sequences` (
	`id` int AUTO_INCREMENT NOT NULL,
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	CONSTRAINT `order_number_sequences_id` PRIMARY KEY(`id`)
);
--> statement-breakpoint
ALTER TABLE `admin_staff` ADD CONSTRAINT `admin_staff_userId_users_id_fk` FOREIGN KEY (`userId`) REFERENCES `users`(`id`) ON DELETE set null ON UPDATE no action;--> statement-breakpoint
CREATE INDEX `admin_audit_created_idx` ON `admin_audit_logs` (`createdAt`);--> statement-breakpoint
CREATE INDEX `admin_staff_role_active_idx` ON `admin_staff` (`roleKey`,`isActive`);