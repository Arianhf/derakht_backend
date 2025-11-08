# Manual Payment Verification Flow

This document describes the manual payment verification flow implemented for the shop.

## Overview

Since we don't have a tax code (کد مالیاتی) yet and cannot get an automatic payment gateway, we've implemented a manual payment verification process where:

1. Users transfer money online to our account
2. Users upload a payment receipt
3. Order status becomes "Awaiting Verification"
4. Admin verifies the payment in the admin panel
5. Admin approves/rejects the payment
6. Order status changes to "Confirmed" or "Cancelled" based on verification

## Changes Made

### 1. New Payment Method Provider
- Added `MANUAL` payment provider to `PaymentMethodProvider` choices
- This allows payments to be marked as manual transfers

### 2. New Order Status
- Added `AWAITING_VERIFICATION` status to `OrderStatus` choices
- This status indicates that a payment receipt has been uploaded and is waiting for admin verification

### 3. Payment Receipt Field
- Added `payment_receipt` ImageField to the `Payment` model
- Users can upload their payment receipt image
- Receipts are stored in `media/payment_receipts/YYYY/MM/DD/`

### 4. Updated Order Status Transitions
- `PENDING` → `AWAITING_VERIFICATION` (when user uploads receipt)
- `AWAITING_VERIFICATION` → `CONFIRMED` (when admin approves)
- `AWAITING_VERIFICATION` → `CANCELLED` (when admin rejects)

### 5. Admin Panel Enhancements

#### Payment Admin
- **Receipt Preview Column**: Shows a thumbnail of the payment receipt in the list view
- **Receipt Image Preview**: Shows a larger preview in the detail view
- **New Actions**:
  - `Verify selected manual payments`: Marks payments as COMPLETED and orders as CONFIRMED
  - `Reject selected manual payments`: Marks payments as FAILED and orders as CANCELLED

## User Flow

1. User creates an order and proceeds to checkout
2. User selects "Manual Transfer" as payment method
3. User transfers money to the provided bank account
4. User uploads payment receipt
5. Payment is created with:
   - `gateway = "MANUAL"`
   - `status = "PENDING"`
   - `payment_receipt = <uploaded_image>`
6. Order status changes to `AWAITING_VERIFICATION`
7. User receives confirmation that payment is being verified

## Admin Flow

1. Admin goes to Django Admin → Shop → Payments
2. Admin filters by:
   - Status: Pending
   - Gateway: Manual Transfer
3. Admin can see payment receipt thumbnails in the list
4. Admin clicks on a payment to view full details and large receipt preview
5. Admin verifies the payment by checking:
   - Receipt is valid
   - Money was received in the bank account
   - Amount matches the order
6. Admin selects the payment(s) and chooses action:
   - **Verify selected manual payments**: If payment is valid
   - **Reject selected manual payments**: If payment is invalid or not received
7. System automatically:
   - Updates payment status to COMPLETED or FAILED
   - Updates order status to CONFIRMED or CANCELLED

## API Integration Notes

To integrate this on the frontend, you'll need to:

1. **Create/Update Payment Endpoint** to accept:
   - `gateway = "MANUAL"`
   - `payment_receipt` (file upload)

2. **Order Status Display**:
   - Show "Awaiting Verification" status to users
   - Provide appropriate messaging about verification timeline

3. **Receipt Upload**:
   - Accept image uploads (JPEG, PNG)
   - Validate file size and type
   - Display upload confirmation

## Database Migration

Run the migration to apply these changes:

```bash
python manage.py migrate shop
```

Migration file: `shop/migrations/0008_add_manual_payment_support.py`

## Files Modified

1. `shop/choices.py` - Added MANUAL payment provider and AWAITING_VERIFICATION status
2. `shop/models/payment.py` - Added payment_receipt field
3. `shop/order_management.py` - Updated status transitions
4. `shop/admin.py` - Enhanced Payment admin with verification actions
5. `shop/migrations/0008_add_manual_payment_support.py` - Database migration

## Future Improvements

- Add email notifications when payment is verified/rejected
- Add notes field for admin to provide rejection reasons
- Add automatic verification timeout
- Integration with banking APIs for automatic verification (when tax code is available)
