FROM node:22-bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends mariadb-server && rm -rf /var/lib/apt/lists/*
WORKDIR /app
RUN corepack enable && corepack prepare pnpm@10.18.0 --activate
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY patches ./patches
RUN CI=1 pnpm install --frozen-lockfile
COPY . .
RUN pnpm build
ENV NODE_ENV=production
ENV PORT=3000
EXPOSE 3000
CMD ["sh", "-c", "mkdir -p /run/mysqld && chown -R mysql:mysql /run/mysqld /var/lib/mysql && mariadbd --user=mysql --datadir=/var/lib/mysql --socket=/run/mysqld/mysqld.sock --bind-address=127.0.0.1 --port=3306 --skip-grant-tables --innodb-buffer-pool-size=16M --performance-schema=OFF & sleep 4 && mariadb -u root -e 'CREATE DATABASE IF NOT EXISTS test;' && node dist/index.js"]
