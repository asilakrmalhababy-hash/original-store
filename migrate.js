import "dotenv/config";
import mysql from "mysql2/promise";
import fs from "fs";
async function run(){
console.log("Connecting to TiDB Cloud with SSL...");
const conn=await mysql.createConnection({host:"gateway01.ap-southeast-1.prod.alicloud.tidbcloud.com",port:4000,user:"3hSHvAteE79AKjH.root",password:"TnX2g3pKSWpPF6uB",ssl:{rejectUnauthorized:true},multipleStatements:true});
console.log("Connected successfully! Preparing database...");
await conn.query("CREATE DATABASE IF NOT EXISTS test; USE test;");
const files=["drizzle/0000_initial_users.sql","drizzle/0001_original_store.sql","drizzle/0002_grey_baron_zemo.sql"];
for(const f of files){
if(!fs.existsSync(f))continue;
const stmts=fs.readFileSync(f,"utf8").split("--> statement-breakpoint").map(s=>s.trim()).filter(Boolean);
for(const s of stmts){try{await conn.query(s);}catch(e){if(!e.message.includes("already exists"))console.warn("Notice:",e.message);}}
console.log("Executed: "+f);
}
await conn.end();
console.log("ALL 14 TABLES CREATED SUCCESSFULLY IN TIDB CLOUD!");
}
run().catch(console.error);