#!/usr/bin/env node
import fs from "fs";
import path from "path";

const ROOT_DIR = process.cwd();

/* Create a set of directories to ignore. We'll scan the directories that aren't in this
   set for security vulnerabilities. This is more robust than targeing specific directories
   in case we add new ones or rename existing ones. */
const IGNORED_DIRS = new Set([
    "node_modules",
    "venv",
    ".git",
    ".pytest_cache",
    ".ruff_cache",
    ".vscode",
    "scripts",
    "tests",
    "docs",
    "data"
]);

function getBackendDirs() {
    /* readdirSync will return an array of strings that represent all folders at ROOT_DIR. For each one, we
       join it to the root directory path to get the full path to that folder. If it's a true directory and
       not part of the set of directories to ignore, include it in the array of strings we return. */
    return fs.readdirSync(ROOT_DIR)
        .filter(name => {
            const full_path = path.join(ROOT_DIR, name);
            return fs.statSync(full_path).isDirectory() && !IGNORED_DIRS.has(name);
        });
}

const BACKEND_DIRS = getBackendDirs(ROOT_DIR);

/* Patterns that often indicate secrets */
const SUSPICIOUS_PATTERNS = [
    "sk_",
    "service_role",
    "AIza",
    "xoxb-",
    "xoxp-",
    "BEGIN PRIVATE KEY",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_ACCESS_KEY_ID",
    "jwt_secret",
    "JWT_SECRET",
    "SECRET_KEY",
    "DATABASE_URL",
    "DB_PASSWORD",
    "DB_USER",
    "ACCESS_TOKEN",
    "REFRESH_TOKEN"
];

/* Returns all files in the specified directory using fileFilter to decide what to 
   include (everything, by default). fileFilter, for example, can be used to 
   restrict scanning to .ts files. */
function getFilesInDir(dir, fileFilter = () => true) {
    const filePaths = [];

    if (!fs.existsSync(dir)) return filePaths;

    /* This list of strings will include the file title plus extension for files and the folder name for directories. */
    const fileAndDirNames = fs.readdirSync(dir);

    for (const item of fileAndDirNames) {
        const fullPath = path.join(dir, item);
        /* This will let us know if the item in the list is a file or directory. */
        const stat = fs.statSync(fullPath);

        /* If the item is a directory, recursively call this function again. */
        if (stat.isDirectory()) {
            filePaths.push(...getFilesInDir(fullPath, fileFilter));
        } 
        /* Otherwise, if it's a file that should be included, add it to the list of file paths. */
        else if (fileFilter(fullPath)) {
            filePaths.push(fullPath);
        }
    }

    return filePaths;
}

function safeReadFile(file) {
    try {
        return fs.readFileSync(file, "utf8");
    } 
    catch {
        return "";
    }
}

function checkEnvFiles() {
    let issues = 0;

    const gitignorePath = path.join(ROOT_DIR, ".gitignore");
    const envPath = path.join(ROOT_DIR, ".env");
    const envExamplePath = path.join(ROOT_DIR, ".env.example");

    /* Get the contents of the gitignore file, if it exists. */
    const gitignoreFileContents = fs.existsSync(gitignorePath)
        ? fs.readFileSync(gitignorePath, "utf8")
        : "";

    /* .env should not be tracked by Git. */
    if (fs.existsSync(envPath)) {
        const tracked = isFileTracked(".env");

        if (tracked) {
            console.error(`[backend-audit] ---WARNING--- .env is being tracked by git. `);
            issues++;
        }
    }

    /* .env should be in .gitignore to avoid committing secrets. */
    if (!gitignoreFileContents.includes(".env")) {
        console.error(`[backend-audit] ---WARNING--- .gitignore does not include ".env".`);
        issues++;
    }

    /* .env.example is good for onboarding and CI. */
    if (!fs.existsSync(envExamplePath)) {
        console.warn(`[backend-audit] ---RECOMMENDATION--- .env.example not found. Consider adding one with placeholder values.`);
    } 

    return issues;
}

function isFileTracked(relPath) {
    try {
        /* Allow Node to run Shell commands synchronously. */
        const { execSync } = require("child_process");

        /* Run the "git ls-files" Shell command from the root directory and return the result as a string (UTF-8). It lists all 
           files that Git knows about (committed, staged, etc.). ignored or untracked files will not be listed. 
           
           stdio: ["ignore", "pipe", "ignore"] <--> stdio: [stdin, stdout, stderr] */
        const out = execSync(`git ls-files ${relPath}`, {
            cwd: ROOT_DIR,
            encoding: "utf8",
            stdio: ["ignore", "pipe", "ignore"]
        });

        /* If there is a file, Git is tracking it. Otherwise, the file is untracked. */
        return out.trim().length > 0;
    } 
    /* In case Git isn't installed, the command fails, the repo isn't installed, etc. */
    catch {
        return false;
    }
}

function fileFilter(filePath) {
    const fileTypesToCheck = [".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".json"];
    /* Include the file (return true) if it ends with one of the file types we need to audit. */
    return fileTypesToCheck.some(ext => filePath.endsWith(ext));
}

function scanBackendFiles() {
    /* For each backend folder at the root, add the file paths in that directory to a single
       array of files. Using flatMap ensures all files for each directory at the root end up in
       a flat array with no nesting. Reminder of map vs flatMap:

            [1, 2, 3].map(n => [n, n * 2]) --> [[1, 2], [2, 4], [3, 6]]
               
                vs

            [1, 2, 3].flatMap(n => [n, n * 2]) --> [1, 2, 2, 4, 3, 6]

    */
    const filePaths = BACKEND_DIRS.flatMap((dir) => getFilesInDir(path.join(ROOT_DIR, dir), fileFilter));

    /* Array of objects, each containing a suspicious pattern and the file it is found in. */
    const findings = [];

    for (const file of filePaths) {
        const content = safeReadFile(file);

        for (const pattern of SUSPICIOUS_PATTERNS) {
            if (content.includes(pattern)) {
                findings.push({
                    pattern,
                    file
                });
            }
        }
    }

    if (findings.length > 0) {
        console.error(`\n[backend-audit] Potential hardcoded secrets found:`);

        for (const f of findings) {
            console.error(`  - "${f.pattern}" in ${path.relative(ROOT_DIR, f.file)}`);
        }
    } 
    else {
        console.log(`[backend-audit] No obvious hardcoded secrets found in backend source code.`);
    }

    return findings.length;
}

function main() {
    let issues = 0;

    issues += checkEnvFiles();
    issues += scanBackendFiles();

    if (issues > 0) {
        console.error(`\n[backend-audit] ---FAIL--- Found ${issues} potential issue(s). `);
        process.exit(1);
    } 
    else {
        console.log(`\n[backend-audit] ---PASS--- No issues encountered.`);
    }
}

main();
