import { OriginMarkSDK, signContent, verifyContent } from './dist/index.js';

const sdk = new OriginMarkSDK('http://localhost:8000');

async function testSDK() {
  try {
    console.log(' Testing OriginMark TypeScript SDK...');
    console.log('=====================================');
    
    // Test local signing
    console.log('\n📝 Testing local content signing...');
    const content = "Hello from TypeScript SDK!";
    const result = await sdk.signContent(content, {
      author: 'SDK Test User',
      model_used: 'Claude 3'
    });
    
    console.log(' Signing successful!');
    console.log('Signature ID:', result.id);
    console.log('Content Hash:', result.content_hash);
    console.log('Public Key:', result.public_key.substring(0, 20) + '...');
    console.log('Timestamp:', result.timestamp);
    console.log('Author:', result.metadata.author);
    
    // Test local verification
    console.log('\n🔍 Testing local content verification...');
    const verification = await sdk.verifyContent(
      content,
      result.signature,
      result.public_key
    );
    
    console.log(' Verification result:', verification.valid ? 'VALID' : 'INVALID');
    console.log('Message:', verification.message);
    console.log('Content Hash:', verification.content_hash);
    
    // Test with different content (should fail)
    console.log('\n Testing with modified content (should fail)...');
    const modifiedVerification = await sdk.verifyContent(
      content + " modified",
      result.signature,
      result.public_key
    );
    
    console.log('Verification result:', modifiedVerification.valid ? 'VALID' : 'INVALID');
    console.log('Message:', modifiedVerification.message);
    
    // Test convenience functions
    console.log('\n Testing convenience functions...');
    
    const convenienceResult = await signContent("Test convenience function", {
      author: 'Convenience Test',
      model_used: 'GPT-4'
    });
    
    const convenienceVerification = await verifyContent(
      "Test convenience function",
      convenienceResult.signature,
      convenienceResult.public_key
    );
    
    console.log(' Convenience function test:', convenienceVerification.valid ? 'PASSED' : 'FAILED');
    
    console.log('\n🎉 All tests completed successfully!');
    
  } catch (error) {
    console.error(' SDK test failed:', error);
    console.error('Stack trace:', error.stack);
  }
}

testSDK();