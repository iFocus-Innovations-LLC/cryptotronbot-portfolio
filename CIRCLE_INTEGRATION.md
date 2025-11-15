# Circle Integration Guide: Secure Stablecoin-to-USD Platform

## Why Circle for MVP

**Circle** is the ideal choice for our first-to-market stablecoin-to-USD platform because:
- **USDC Creator**: Circle is the issuer of USD Coin (USDC) - natural integration
- **Established Infrastructure**: Years of regulatory compliance and banking relationships
- **Developer-Friendly**: Well-documented APIs and SDKs
- **Compliance Built-In**: KYC/AML, regulatory reporting already handled
- **Trust & Reliability**: Public company with transparent operations

## Circle API Overview

### Circle API v2
**Base URL**: `https://api.circle.com/v1` (v1 is current, v2 coming)  
**Documentation**: https://developers.circle.com/  
**SDK**: Python SDK available

### Key Features
- **Programmable Wallets**: Create and manage wallets
- **USDC Transfers**: Native USDC support
- **Bank Account Linking**: Connect user bank accounts
- **Wire Transfers**: Convert USDC to USD and send to banks
- **Webhooks**: Real-time transaction status updates
- **KYC/AML**: Built-in compliance features

## Integration Architecture

### High-Level Flow with Circle

```
User Portfolio (USDC) → Circle Wallet → Circle Wire Transfer API → 
USD Deposit → User Bank Account
```

### Circle API Endpoints We'll Use

1. **Wallets API**
   - Create wallet for user
   - Get wallet balance (USDC)
   - List wallets

2. **Transfers API**
   - Create wire transfer (USDC → USD → Bank)
   - Get transfer status
   - List transfers

3. **Bank Accounts API**
   - Link bank account
   - Verify bank account
   - List bank accounts

4. **Webhooks API**
   - Receive transaction status updates
   - Handle transfer confirmations

## Circle Integration Setup

### Step 1: Circle Account Setup

```bash
# 1. Sign up at https://console.circle.com
# 2. Create API key (sandbox for testing)
# 3. Enable required APIs:
#    - Wallets
#    - Transfers
#    - Bank Accounts
#    - Webhooks
```

### Step 2: Environment Configuration

```python
# .env file
CIRCLE_API_KEY=your_circle_api_key_here
CIRCLE_API_URL=https://api-sandbox.circle.com  # Sandbox
# CIRCLE_API_URL=https://api.circle.com  # Production

CIRCLE_WEBHOOK_SECRET=your_webhook_secret
CIRCLE_ENVIRONMENT=sandbox  # or 'production'
```

### Step 3: Install Circle SDK

```bash
pip install circle-python-sdk
# or
pip install circle-python
```

## Circle API Implementation

### Wallet Management

```python
from circle import CircleClient

class CircleWalletManager:
    """Manages Circle wallet operations for users"""
    
    def __init__(self, api_key: str, api_url: str = None):
        self.client = CircleClient(api_key=api_key, api_url=api_url)
    
    def create_wallet_for_user(self, user_id: str, description: str = None):
        """Create a Circle wallet for a user"""
        wallet = self.client.wallets.create({
            'idempotencyKey': f"wallet_{user_id}_{datetime.utcnow().timestamp()}",
            'description': description or f"Wallet for user {user_id}"
        })
        return wallet
    
    def get_wallet_balance(self, wallet_id: str):
        """Get USDC balance for a wallet"""
        balance = self.client.wallets.get_balance(wallet_id)
        return balance
    
    def get_user_wallet(self, user_id: str):
        """Retrieve or create wallet for user"""
        # Check if wallet exists in database
        # If not, create one via Circle API
        pass
```

### Bank Account Management

```python
class CircleBankAccountManager:
    """Manages bank account linking via Circle"""
    
    def __init__(self, api_key: str):
        self.client = CircleClient(api_key=api_key)
    
    def link_bank_account(self, user_id: str, bank_details: dict):
        """Link user's bank account via Circle"""
        bank_account = self.client.bank_accounts.create({
            'idempotencyKey': f"bank_{user_id}_{datetime.utcnow().timestamp()}",
            'accountNumber': bank_details['account_number'],
            'routingNumber': bank_details['routing_number'],
            'accountType': bank_details['type'],  # 'checking' or 'savings'
            'bankName': bank_details['bank_name'],
            'currency': 'USD',
            'billingDetails': {
                'name': bank_details['account_holder_name'],
                'line1': bank_details['address_line1'],
                'city': bank_details['city'],
                'district': bank_details['state'],
                'postalCode': bank_details['zip'],
                'country': 'US'
            }
        })
        return bank_account
    
    def verify_bank_account(self, bank_account_id: str, amounts: list):
        """Verify bank account with micro-deposits"""
        verification = self.client.bank_accounts.verify(bank_account_id, {
            'amounts': amounts  # Micro-deposit amounts
        })
        return verification
    
    def list_user_bank_accounts(self, user_id: str):
        """List all bank accounts for a user"""
        accounts = self.client.bank_accounts.list()
        return accounts
```

### Transfer Management (USDC to USD)

```python
class CircleTransferManager:
    """Manages USDC to USD transfers via Circle"""
    
    def __init__(self, api_key: str):
        self.client = CircleClient(api_key=api_key)
    
    def create_usdc_to_usd_transfer(self, wallet_id: str, bank_account_id: str, 
                                    usdc_amount: str):
        """
        Create a transfer: USDC from wallet → USD to bank account
        
        This is the core transaction for our platform
        """
        transfer = self.client.transfers.create({
            'idempotencyKey': f"transfer_{uuid.uuid4()}",
            'source': {
                'type': 'wallet',
                'id': wallet_id
            },
            'destination': {
                'type': 'wire',
                'id': bank_account_id
            },
            'amount': {
                'amount': usdc_amount,
                'currency': 'USDC'
            }
        })
        return transfer
    
    def get_transfer_status(self, transfer_id: str):
        """Get current status of a transfer"""
        transfer = self.client.transfers.get(transfer_id)
        return transfer
    
    def list_user_transfers(self, wallet_id: str):
        """List all transfers for a wallet"""
        transfers = self.client.transfers.list({
            'source': wallet_id
        })
        return transfers
```

### Webhook Handler

```python
from flask import request
import hmac
import hashlib

class CircleWebhookHandler:
    """Handles Circle webhook notifications"""
    
    def __init__(self, webhook_secret: str):
        self.webhook_secret = webhook_secret
    
    def verify_webhook_signature(self, payload: str, signature: str) -> bool:
        """Verify webhook signature from Circle"""
        expected_signature = hmac.new(
            self.webhook_secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected_signature, signature)
    
    def handle_webhook(self, payload: dict):
        """Handle incoming webhook from Circle"""
        event_type = payload.get('type')
        data = payload.get('data')
        
        if event_type == 'transfer.created':
            self._handle_transfer_created(data)
        elif event_type == 'transfer.confirmed':
            self._handle_transfer_confirmed(data)
        elif event_type == 'transfer.failed':
            self._handle_transfer_failed(data)
        elif event_type == 'bank_account.verified':
            self._handle_bank_verified(data)
    
    def _handle_transfer_confirmed(self, transfer_data: dict):
        """Update transaction status when transfer is confirmed"""
        transfer_id = transfer_data.get('id')
        # Update database transaction status to 'COMPLETED'
        pass
```

## Flask API Integration

### Transaction Initiation Endpoint

```python
@app.route('/api/transactions/circle/initiate', methods=['POST'])
@jwt_required()
def initiate_circle_transaction():
    """Initiate USDC to USD transfer via Circle"""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user:
        return jsonify({"msg": "User not found"}), 404
    
    data = request.get_json()
    usdc_amount = data.get('usdc_amount')
    bank_account_id = data.get('bank_account_id')
    
    # Validate input
    if not usdc_amount or not bank_account_id:
        return jsonify({"msg": "Missing required fields"}), 400
    
    # Get or create user's Circle wallet
    wallet_manager = CircleWalletManager(api_key=os.getenv('CIRCLE_API_KEY'))
    wallet = wallet_manager.get_user_wallet(user.id)
    
    # Check wallet balance
    balance = wallet_manager.get_wallet_balance(wallet['id'])
    if float(balance['amount']) < float(usdc_amount):
        return jsonify({"msg": "Insufficient USDC balance"}), 400
    
    # Create transfer via Circle
    transfer_manager = CircleTransferManager(api_key=os.getenv('CIRCLE_API_KEY'))
    transfer = transfer_manager.create_usdc_to_usd_transfer(
        wallet_id=wallet['id'],
        bank_account_id=bank_account_id,
        usdc_amount=usdc_amount
    )
    
    # Create transaction record in database
    transaction = Transaction(
        user_id=user.id,
        transaction_type='stablecoin_to_usd',
        status='PENDING',
        stablecoin_symbol='USDC',
        stablecoin_amount=usdc_amount,
        processor='circle',
        processor_transaction_id=transfer['id'],
        processor_status=transfer['status']
    )
    db.session.add(transaction)
    db.session.commit()
    
    return jsonify({
        "transaction_id": transaction.id,
        "circle_transfer_id": transfer['id'],
        "status": transfer['status'],
        "estimated_completion": transfer.get('estimated_completion')
    }), 201
```

## Circle-Specific Transaction Flow

### Complete User Journey

1. **User Authentication** (JWT)
2. **Link Bank Account** → Circle Bank Accounts API
3. **Verify Bank Account** → Micro-deposit verification
4. **Create Circle Wallet** → Circle Wallets API (if needed)
5. **Check USDC Balance** → Circle Wallets API
6. **Initiate Transfer** → Circle Transfers API
7. **Monitor Status** → Circle Webhooks + Status API
8. **Complete** → USD deposited to bank account

## Testing with Circle Sandbox

### Sandbox Environment
- **API URL**: `https://api-sandbox.circle.com`
- **Test Cards**: Provided in Circle dashboard
- **Test Bank Accounts**: Circle provides test routing numbers
- **No Real Money**: All transactions are simulated

### Testing Checklist
- [ ] Create test wallet
- [ ] Link test bank account
- [ ] Verify bank account (test micro-deposits)
- [ ] Initiate test transfer
- [ ] Verify webhook handling
- [ ] Test error scenarios

## Production Deployment

### Production Setup
1. **Circle Production Account**
   - Complete KYC/AML verification
   - Enable production APIs
   - Configure webhook endpoints
   - Set up monitoring

2. **Security Configuration**
   - Rotate API keys regularly
   - Use Google Secret Manager for keys
   - Enable webhook signature verification
   - Monitor all transactions

3. **Compliance**
   - Circle handles most compliance
   - We track transactions for audit
   - Implement transaction limits
   - Monitor for suspicious activity

## Circle API Rate Limits

- **Rate Limits**: Check Circle documentation for current limits
- **Best Practice**: Implement exponential backoff
- **Caching**: Cache wallet balances (15 min)
- **Webhooks**: Prefer webhooks over polling

## Error Handling

### Common Circle API Errors

```python
CIRCLE_ERROR_CODES = {
    'insufficient_funds': 'Insufficient USDC balance',
    'bank_account_unverified': 'Bank account not verified',
    'invalid_account': 'Invalid bank account details',
    'rate_limit': 'Rate limit exceeded',
    'network_error': 'Network error, retry later'
}
```

## Resources

- **Circle Developer Docs**: https://developers.circle.com/
- **Circle API Reference**: https://developers.circle.com/reference
- **Circle Python SDK**: https://github.com/circlefin/circle-python
- **Circle Status**: https://status.circle.com/
- **Circle Support**: support@circle.com

## Next Steps for Sprint 1

1. **Day 3**: Set up Circle sandbox account
2. **Day 4**: Implement Circle wallet management
3. **Day 5**: Implement bank account linking
4. **Day 6**: Implement transfer creation
5. **Day 7**: Test end-to-end flow

---

**Created**: January 22, 2025  
**Status**: Ready for Implementation  
**Priority**: High - Primary Payment Processor

