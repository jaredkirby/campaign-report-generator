const path = require('path');
const CampaignProcessor = require('../lib/campaignProcessor');

async function main() {
  const config = {
    inputPath: path.join(process.cwd(), 'data', 'uploads', 'current.csv'),
    historyPath: path.join(process.cwd(), 'data', 'history', 'latest.json'),
    markdownPath: path.join(process.cwd(), 'data', 'output', `report_${Date.now()}.md`),
    textPath: path.join(process.cwd(), 'data', 'output', `report_${Date.now()}.txt`),
  };

  const processor = new CampaignProcessor(config);
  const result = await processor.process();

  if (result.success) {
    console.log('Processing completed successfully');
    console.log(`Processed ${result.campaignCount} campaigns`);
    console.log(`Detected ${result.changesDetected} changes`);
    console.log('Reports generated at:');
    console.log(`- Markdown: ${result.reportPaths.markdown}`);
    console.log(`- Text: ${result.reportPaths.text}`);
  } else {
    console.error('Processing failed:', result.error);
    process.exit(1);
  }
}

main().catch(error => {
  console.error('Unexpected error:', error);
  process.exit(1);
});