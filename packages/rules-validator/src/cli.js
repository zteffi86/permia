#!/usr/bin/env node
import fs from 'fs';
import path from 'path';
import Ajv from 'ajv';
import addFormats from 'ajv-formats';
import { glob } from 'glob';

const rulesDir = process.argv[2] || './rules';
const schemaPath = path.join(rulesDir, 'schemas/rule_schema_v23.3.0.json');
const statuteRegistryPath = path.join(rulesDir, 'statute-registry.json');
const normDefsDir = path.join(rulesDir, 'normative-definitions');

const schema = JSON.parse(fs.readFileSync(schemaPath, 'utf-8'));
const ajv = new Ajv({ allErrors: true, strict: true });
addFormats(ajv);
const validate = ajv.compile(schema);

let statuteRegistry = {};
if (fs.existsSync(statuteRegistryPath)) {
  statuteRegistry = JSON.parse(fs.readFileSync(statuteRegistryPath, 'utf-8'));
}

let failed = 0;
const errors = [];

const ruleFiles = await glob(`${rulesDir}/**/rule.json`, {
  ignore: ['**/node_modules/**', '**/schemas/**'],
});

console.log(`\n🔍 Validating ${ruleFiles.length} rules...\n`);

for (const ruleFile of ruleFiles) {
  const ruleDir = path.dirname(ruleFile);
  const ruleName = path.basename(ruleDir);

  try {
    const ruleData = JSON.parse(fs.readFileSync(ruleFile, 'utf-8'));

    if (!validate(ruleData)) {
      errors.push(`❌ ${ruleName}: Schema validation failed`);
      validate.errors.forEach(err => {
        errors.push(`   ${err.instancePath} ${err.message}`);
      });
      failed++;
      continue;
    }

    const metaPath = path.join(ruleDir, 'meta.yaml');
    if (!fs.existsSync(metaPath)) {
      errors.push(`❌ ${ruleName}: Missing meta.yaml`);
      failed++;
      continue;
    }

    const fixturesDir = path.join(ruleDir, 'fixtures');
    if (!fs.existsSync(fixturesDir)) {
      errors.push(`❌ ${ruleName}: Missing fixtures/ directory`);
      failed++;
      continue;
    }

    const fixtures = fs.readdirSync(fixturesDir).filter(f => f.endsWith('.json'));
    if (fixtures.length < 3) {
      errors.push(`❌ ${ruleName}: Need ≥3 fixtures (found ${fixtures.length})`);
      failed++;
      continue;
    }

    const legalRefs = ruleData.jurisdictional_logic?.legal_references || [];
    for (const ref of legalRefs) {
      if (ref.statute_id && !statuteRegistry[ref.statute_id]) {
        errors.push(`⚠️  ${ruleName}: Statute ID not found in registry: ${ref.statute_id}`);
      }
    }

    const ruleJson = JSON.stringify(ruleData);
    const normDefMatches = ruleJson.match(/"(ND-\d+)"/g);
    if (normDefMatches) {
      const normDefIds = [...new Set(normDefMatches.map(m => m.replace(/"/g, '')))];
      for (const normDefId of normDefIds) {
        const normDefPath = path.join(normDefsDir, `${normDefId}.json`);
        if (!fs.existsSync(normDefPath)) {
          errors.push(`❌ ${ruleName}: Normative definition not found: ${normDefId}`);
          failed++;
        }
      }
    }

    const hasAssertions =
      (ruleData.validation?.must_meet_threshold?.length > 0) ||
      (ruleData.validation?.must_include?.length > 0) ||
      (ruleData.validation?.ai_checks?.length > 0);

    if (!hasAssertions) {
      errors.push(`⚠️  ${ruleName}: No assertions defined`);
    }

    console.log(`✅ ${ruleName}`);

  } catch (e) {
    errors.push(`❌ ${ruleName}: ${e.message}`);
    failed++;
  }
}

console.log(`\n${'='.repeat(60)}\n`);
if (failed > 0) {
  console.log(`❌ ${failed} rule(s) failed validation:\n`);
  errors.forEach(err => console.log(err));
  process.exit(1);
} else {
  console.log(`✅ All ${ruleFiles.length} rules passed validation`);
  process.exit(0);
}
