# RTO Autopilot - Complete User Guide with Screenshot Points

This guide provides step-by-step instructions for using all features of RTO Autopilot. Follow each step and take screenshots at the marked points for your README documentation.

## Prerequisites

Before starting, ensure:
- The app is running (`uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`)
- You have access to the app at `http://localhost:8000` (or your deployed URL)
- Your browser is opened to the app

---

## Step 1: Landing Page

**URL**: `http://localhost:8000`

### What to Do:
1. Open your browser and navigate to the app's URL
2. Observe the landing page with RTO Autopilot branding

### 📸 SCREENSHOT POINT #1: Landing Page
- **Capture**: Full landing page showing:
  - RTO Autopilot logo/hero section
  - "Login to Your Office" button
  - "Create New Office" button
  - Feature cards (Case Management, AI-Powered Intake, Analytics & Insights)
  - Additional features section (Automated Reminders, Smart Checklists, Secure Data Management, 24/7 Status Tracking)

### What to Observe:
- Clean, professional design with Tailwind styling
- Blue color scheme matching primary-600 (#447090)
- Responsive layout (works on mobile and desktop)
- Clear call-to-action buttons

---

## Step 2: Create New Office (First-Time Setup)

**URL**: `http://localhost:8000/signup`

### What to Do:
1. Click "Create New Office" button on the landing page
2. Fill in the office creation form:
   - **Office Name**: Enter "Demo RTO Office" (or your preferred name)
   - **Office Code**: Enter "demo-rto" (must be unique, lowercase, hyphens only)
   - **Admin Email**: Enter your email (e.g., admin@demo.com)
   - **Admin Password**: Enter a secure password (min 8 characters)
   - **Admin Full Name**: Enter "Demo Admin"
   - **Display Name**: Optional (e.g., "Demo RTO")
3. Click "Create Office" button

### 📸 SCREENSHOT POINT #2: Signup Page (Before Submission)
- **Capture**: The signup form with filled-in fields before clicking submit
- **Show**: All form fields filled with example data

### 📸 SCREENSHOT POINT #3: Signup Success
- **Capture**: Success message after office creation
- **Expected**: "Office created successfully! You can now log in." message

### What Happens:
- A new office record is created in the database
- An admin staff account is created
- Default checklist configurations are set up for common service types
- You're redirected to the login page

---

## Step 3: Login

**URL**: `http://localhost:8000/login`

### What to Do:
1. After signup, you'll be redirected to the login page (or navigate manually)
2. Enter the credentials you just created:
   - **Email**: admin@demo.com (or the email you used)
   - **Password**: The password you set during signup
3. Click "Sign in" button

### 📸 SCREENSHOT POINT #4: Login Page (Before Submission)
- **Capture**: Login form with filled credentials
- **Show**: Email and password fields filled

### 📸 SCREENSHOT POINT #5: Dashboard After Login
- **Capture**: Dashboard page immediately after successful login
- **Show**:
  - Welcome message with your name
  - Office name in navigation bar
  - Action buttons (Add Customer, New Case)
  - Recent cases list (empty initially)
  - Statistics cards (if any data exists)

### What to Observe:
- Navigation bar shows office name: "RTO Autopilot — Demo RTO Office"
- Admin-specific buttons are visible (Data Deletion, Audit Log)
- Mobile menu button (hamburger icon) appears on smaller screens

---

## Step 4: Dashboard Overview

**URL**: `http://localhost:8000/dashboard`

### What to Do:
1. Explore the dashboard interface
2. Note the different sections:
   - Header with welcome message
   - Action buttons
   - Recent cases table
   - Statistics (if populated)

### 📸 SCREENSHOT POINT #6: Dashboard Navigation
- **Capture**: Dashboard showing the navigation bar
- **Show**:
  - Top navigation with all menu items
  - Office name
  - Mobile menu button (on smaller screens)
  - Logout button

### 📸 SCREENSHOT POINT #7: Dashboard Action Buttons
- **Capture**: Zoom in on the action buttons area
- **Show**:
  - "Add Customer" button (green)
  - "New Case" button (blue)
  - "Data Deletion" button (red, admin only)
  - "Audit Log" button (purple, admin only)

### 📸 SCREENSHOT POINT #8: Mobile Menu (Optional - Test on Mobile or Small Window)
- **Capture**: Click the hamburger menu to show mobile navigation
- **Show**: All navigation links in the mobile dropdown menu
- **Test on Phone**: Open on your phone to show PWA install prompt

---

## Step 5: Add Customer

**URL**: `http://localhost:8000/add-customer`

### What to Do:
1. Click "Add Customer" button in the dashboard
2. Fill in the customer form:
   - **Full Name**: Enter "John Doe"
   - **Phone**: Enter "9876543210"
   - **Email**: Enter "john.doe@example.com"
   - **Address**: Enter "123 Main Street, Bangalore"
   - **Aadhaar Number**: Enter "1234-5678-9012" (or leave blank if optional)
3. Click "Add Customer" button

### 📸 SCREENSHOT POINT #9: Add Customer Form (Before Submission)
- **Capture**: The add customer form with filled fields
- **Show**: All form fields filled with example customer data

### 📸 SCREENSHOT POINT #10: Customer Added Success
- **Capture**: Success message after adding customer
- **Expected**: "Customer added successfully!" message
- **Show**: Redirect back to dashboard with new customer in the dropdown/list

### What Happens:
- Customer record is created in the database
- Associated with your office (office isolation)
- Customer becomes available for new case creation

---

## Step 6: Create New Case

**URL**: `http://localhost:8000/new-case`

### What to Do:
1. Click "New Case" button in the dashboard
2. Select the customer you just added from the dropdown
3. Fill in case details:
   - **Service Type**: Select "New Registration" (or another option)
   - **Vehicle Number**: Enter "KA-01-AB-1234"
   - **Vehicle Type**: Select "Two Wheeler" (or appropriate type)
   - **Description**: Enter "New vehicle registration for Honda Activa"
4. Upload required documents (if any checklist items exist):
   - Click "Choose File" for each required document
   - Select a test PDF or image file
5. Click "Create Case" button

### 📸 SCREENSHOT POINT #11: New Case Form (Before Submission)
- **Capture**: The new case form with filled details
- **Show**:
  - Customer dropdown with selected customer
  - Service type selection
  - Vehicle details filled
  - Document upload sections (if checklist exists)

### 📸 SCREENSHOT POINT #12: Case Created Success
- **Capture**: Success message after case creation
- **Expected**: "Case created successfully!" message
- **Show**: Redirect to case detail page

### What Happens:
- Case record is created in the database
- Documents are uploaded to R2 storage (if configured)
- Event is logged in the audit trail
- Case is associated with your office

---

## Step 7: View Case Details

**URL**: `http://localhost:8000/case/{case_id}` (auto-redirected after case creation)

### What to Do:
1. After creating a case, you'll be redirected to the case detail page
2. Explore the case detail sections:
   - Case information header
   - Customer information
   - Status indicator
   - Document list
   - Event history
   - Action buttons

### 📸 SCREENSHOT POINT #13: Case Detail Page
- **Capture**: Full case detail page
- **Show**:
  - Case ID and status badge
  - Customer information section
  - Service type and vehicle details
  - Document uploads section
  - Event history timeline
  - Action buttons (Upload Document, Generate PDF, Update Status)

### 📸 SCREENSHOT POINT #14: Document Upload Section
- **Capture**: Zoom in on the document upload area
- **Show**:
  - Existing documents (if any)
  - Upload form with file input
  - Document status indicators

### 📸 SCREENSHOT POINT #15: Event History Timeline
- **Capture**: Event history section showing case timeline
- **Show**:
  - Case creation event
  - Document upload events
  - Status change events
  - Timestamps for each event

---

## Step 8: Upload Additional Documents

**URL**: `http://localhost:8000/case/{case_id}`

### What to Do:
1. On the case detail page, click "Upload Document" button
2. Select a file from your computer (PDF or image)
3. Enter a document description (e.g., "Vehicle Insurance Copy")
4. Click "Upload" button

### 📸 SCREENSHOT POINT #16: Document Upload Form
- **Capture**: Document upload modal or form
- **Show**:
  - File input with selected file
  - Description field
  - Upload button

### 📸 SCREENSHOT POINT #17: Document Uploaded Success
- **Capture**: Success message after document upload
- **Expected**: "Document uploaded successfully!" message
- **Show**: New document appears in the document list

### What Happens:
- Document is uploaded to R2 storage
- Document record is created in database
- Event is logged in case history
- Document is linked to the case

---

## Step 9: Generate Case PDF

**URL**: `http://localhost:8000/case/{case_id}`

### What to Do:
1. On the case detail page, click "Generate PDF" button
2. Wait for PDF generation
3. PDF will be downloaded automatically

### 📸 SCREENSHOT POINT #18: Generate PDF Button
- **Capture**: Case detail page with "Generate PDF" button highlighted
- **Show**: The button and surrounding case information

### 📸 SCREENSHOT POINT #19: Generated PDF (Open the Downloaded File)
- **Capture**: Open the downloaded PDF file
- **Show**: PDF content with case details, customer info, and document list

### What Happens:
- PDF is generated with all case information
- Includes customer details, service type, documents, and event history
- PDF is downloaded to your computer

---

## Step 10: AI-Powered Intake (Conversational Form)

**URL**: `http://localhost:8000/intake`

### What to Do:
1. Click "AI Intake" in the navigation bar
2. Wait for the AI assistant to greet you
3. Type a natural language message, e.g.:
   - "I want to register a new vehicle"
   - "I need to renew my driving license"
   - "I want to transfer ownership of my car"
4. Follow the AI's questions and provide information
5. When the AI has collected all information, it will offer to create a case
6. Click "Submit" to create the case from the conversation

### 📸 SCREENSHOT POINT #20: AI Intake Chat Interface
- **Capture**: AI intake page with initial greeting
- **Show**:
  - Chat interface with message bubbles
  - AI greeting message
  - Text input field
  - Send button

### 📸 SCREENSHOT POINT #21: AI Conversation in Progress
- **Capture**: Mid-conversation with AI
- **Show**:
  - Multiple message exchanges
  - AI asking questions
  - Your responses
  - Typing indicator (if visible)

### 📸 SCREENSHOT POINT #22: AI Ready to Submit
- **Capture**: AI has collected all information and shows submit option
- **Show**:
  - Summary of collected data
  - "Submit" button to create case
  - Service type identified by AI

### 📸 SCREENSHOT POINT #23: Case Created from AI Intake
- **Capture**: Success message after case creation from AI
- **Expected**: "Case created successfully!" message
- **Show**: Redirect to case detail page

### What Happens:
- AI uses Groq API to understand user intent
- AI identifies service type and collects required information
- Data is structured and validated
- Case is created with collected information
- Event is logged with "AI Intake" source

---

## Step 11: Check Status (Public Feature)

**URL**: `http://localhost:8000/status`

### What to Do:
1. Click "Check Status" in the navigation bar
2. Enter a case ID (use the ID from a case you created)
3. Click "Check Status" button

### 📸 SCREENSHOT POINT #24: Status Check Page (Before Submission)
- **Capture**: Status check form with case ID input
- **Show**: Empty form with case ID field

### 📸 SCREENSHOT POINT #25: Status Check Result
- **Capture**: Status result after submission
- **Show**:
  - Case details (if found)
  - Current status
  - Last updated timestamp
  - Or "Case not found" message if invalid ID

### What Happens:
- System searches for case by ID
- Returns current status if found
- Accessible without login (public feature)
- Useful for customers to check their case status

---

## Step 12: Reminders (Automated Document Requests)

**URL**: `http://localhost:8000/reminders`

### What to Do:
1. Click "Reminders" in the navigation bar
2. View the list of pending reminders
3. If no reminders exist, click "Trigger Reminder Check" to simulate
4. Review drafted reminder messages
5. Click "Approve" to send reminder to customer
6. Or click "Reject" to dismiss the reminder

### 📸 SCREENSHOT POINT #26: Reminders Page
- **Capture**: Reminders list page
- **Show**:
  - List of pending reminders
  - Reminder details (case, customer, document type)
  - Drafted message preview
  - Approve/Reject buttons

### 📸 SCREENSHOT POINT #27: Reminder Approval
- **Capture**: After clicking "Approve" on a reminder
- **Show**: Success message "Reminder sent successfully!"

### What Happens:
- System checks for cases needing documents (2+ days after request)
- Drafts reminder messages automatically
- Staff reviews and approves/dismisses
- Approved reminders are sent via email (if Resend is configured)
- Events are logged in audit trail

---

## Step 13: Analytics Dashboard

**URL**: `http://localhost:8000/analytics`

### What to Do:
1. Click "Analytics" in the navigation bar
2. Explore the analytics dashboard:
   - Case volume chart
   - Service type distribution
   - Status breakdown
   - Date range filters
3. Adjust date range if desired
4. Observe real-time data updates

### 📸 SCREENSHOT POINT #28: Analytics Dashboard
- **Capture**: Full analytics dashboard
- **Show**:
  - Case volume chart (line or bar graph)
  - Service type distribution (pie chart)
  - Status breakdown
  - Date range filters
  - Summary statistics

### 📸 SCREENSHOT POINT #29: Analytics Charts (Zoom in)
- **Capture**: Individual charts close-up
- **Show**: Clear view of data visualizations

### What Happens:
- Analytics are generated from database queries
- Real-time data from your office
- Date range filtering for custom periods
- Visual representation of case trends

---

## Step 14: Admin - Checklist Management

**URL**: `http://localhost:8000/admin/checklist` (Admin only)

### What to Do:
1. Click "Admin" dropdown in navigation
2. Select "Checklists"
3. View existing service types and their document requirements
4. Add a new service type:
   - Enter service name (e.g., "Vehicle Transfer")
   - Click "Add Service Type"
5. Add documents to a service type:
   - Select service type
   - Enter document name (e.g., "Transfer Form")
   - Check "Required" if mandatory
   - Click "Add Document"
6. Toggle document requirements
7. Reorder documents if needed

### 📸 SCREENSHOT POINT #30: Admin Checklist Page
- **Capture**: Checklist management page
- **Show**:
  - List of service types
  - Document requirements for each service
  - Add service type form
  - Add document form

### 📸 SCREENSHOT POINT #31: Adding a Service Type
- **Capture**: Form to add new service type
- **Show**: Service type input field and add button

### 📸 SCREENSHOT POINT #32: Adding a Document Requirement
- **Capture**: Form to add document to service type
- **Show**:
  - Service type dropdown
  - Document name input
  - Required checkbox
  - Add button

### 📸 SCREENSHOT POINT #33: Checklist After Updates
- **Capture**: Updated checklist with new service type and documents
- **Show**: The newly added items in the checklist

### What Happens:
- Service types define what services your office offers
- Document requirements are enforced during case creation
- Checklists are office-specific (multi-tenant)
- Changes apply to new cases immediately

---

## Step 15: Admin - Data Deletion

**URL**: `http://localhost:8000/admin/data-deletion` (Admin only)

### What to Do:
1. Click "Admin" dropdown in navigation
2. Select "Data Deletion"
3. Search for a customer by name or email
4. View customer details and associated cases
5. Click "Delete Customer" button
6. Confirm deletion in the warning modal
7. Observe success message

### 📸 SCREENSHOT POINT #34: Data Deletion Page
- **Capture**: Data deletion search page
- **Show**:
  - Search form (name/email)
  - Customer search results
  - Customer details with associated cases

### 📸 SCREENSHOT POINT #35: Delete Confirmation Modal
- **Capture**: Warning modal before deletion
- **Show**:
  - Warning message about data loss
  - Confirm/Cancel buttons
  - List of data to be deleted

### 📸 SCREENSHOT POINT #36: Deletion Success
- **Capture**: Success message after deletion
- **Expected**: "Customer and all associated data deleted successfully!"

### What Happens:
- Customer record is deleted
- All associated cases are deleted
- All documents are deleted from R2 storage
- Events are logged in audit trail
- Deletion is irreversible (security feature)

---

## Step 16: Admin - Audit Log

**URL**: `http://localhost:8000/admin/audit-log` (Admin only)

### What to Do:
1. Click "Admin" dropdown in navigation
2. Select "Audit Log"
3. View the complete audit trail of all operations
4. Filter by event type if desired
5. Scroll through recent events
6. Observe detailed event information

### 📸 SCREENSHOT POINT #37: Audit Log Page
- **Capture**: Full audit log page
- **Show**:
  - Table of audit events
  - Event type, timestamp, user, and details
  - Filter options (if available)
  - Pagination controls

### 📸 SCREENSHOT POINT #38: Audit Log Details (Zoom in)
- **Capture**: Close-up of individual audit entries
- **Show**:
  - Event ID
  - Event type (login, case_created, document_uploaded, etc.)
  - Timestamp
  - Staff user who performed action
  - Detailed event data

### What Happens:
- All significant operations are logged
- Includes login attempts, case operations, data changes
- Immutable audit trail for compliance
- Cannot be deleted or modified
- Office-specific (only shows your office's events)

---

## Step 17: PWA Installation (Mobile Only)

### What to Do:
1. Open the app on your mobile phone (must be HTTPS)
2. Wait for the "Add to Home Screen" prompt
3. If prompt doesn't appear:
   - **Android (Chrome)**: Tap ⋮ menu > "Add to Home Screen"
   - **iPhone (Safari)**: Tap Share button > "Add to Home Screen"
4. Confirm installation
5. Tap the app icon on your home screen
6. Observe app opening in standalone mode

### 📸 SCREENSHOT POINT #39: Add to Home Screen Prompt (Android)
- **Capture**: Chrome browser showing "Add to Home Screen" prompt
- **Show**: The prompt with app icon and name

### 📸 SCREENSHOT POINT #40: App Icon on Home Screen
- **Capture**: Home screen with RTO Autopilot app icon
- **Show**: The "RA" icon on your phone's home screen

### 📸 SCREENSHOT POINT #41: App in Standalone Mode
- **Capture**: App opened from home screen
- **Show**:
  - No browser address bar
  - Full-screen app experience
  - App icon in app switcher

### 📸 SCREENSHOT POINT #42: Offline Mode
- **Capture**: Turn off WiFi/data, open the app
- **Show**: "You're Offline" page with retry button

### What Happens:
- App installs with your custom icon and name
- Opens in standalone mode (no browser UI)
- Works offline with cached content
- Settings and theme color are applied

---

## Step 18: Logout

**URL**: `http://localhost:8000/logout`

### What to Do:
1. Click "Logout" in the navigation bar (or mobile menu)
2. Confirm logout if prompted
3. Observe redirect to login page

### 📸 SCREENSHOT POINT #43: Logout Button
- **Capture**: Navigation bar with logout button highlighted
- **Show**: Logout button in the menu

### 📸 SCREENSHOT POINT #44: Login Page After Logout
- **Capture**: Login page after successful logout
- **Show**: Clean login page ready for next login

### What Happens:
- Session is cleared
- User is redirected to login page
- Security measure to prevent unauthorized access

---

## Step 19: Forgot Password Flow

**URL**: `http://localhost:8000/forgot-password`

### What to Do:
1. On the login page, click "Forgot your password?" link
2. Enter your email address
3. Click "Send Reset Link" button
4. Check your email for reset link (if Resend is configured)
5. Click the reset link in the email
6. Enter new password (min 8 characters)
7. Confirm new password
8. Click "Reset Password" button
9. Login with new password

### 📸 SCREENSHOT POINT #45: Forgot Password Page
- **Capture**: Forgot password form
- **Show**: Email input field and send button

### 📸 SCREENSHOT POINT #46: Forgot Password Success
- **Capture**: Success message after sending reset link
- **Expected**: "If an account with this email exists, a password reset link has been sent."

### 📸 SCREENSHOT POINT #47: Reset Password Page
- **Capture**: Reset password form (from email link)
- **Show**:
  - New password field
  - Confirm password field
  - Reset button

### 📸 SCREENSHOT POINT #48: Password Reset Success
- **Capture**: Success message after password reset
- **Expected**: "Password reset successfully! You can now log in."

### What Happens:
- Secure token is generated and emailed
- Token expires after 1 hour
- User can set new password via link
- Old password is invalidated
- Session is cleared for security

---

## Step 20: Account Lockout (Security Feature)

### What to Do:
1. Go to login page
2. Enter correct email but wrong password 5 times
3. Observe account lockout message
4. Wait 15 minutes (or reset via admin/database)
5. Try logging in again with correct password

### 📸 SCREENSHOT POINT #49: Account Lockout Message
- **Capture**: Login page with lockout error
- **Show**: "Account locked due to too many failed attempts. Try again in 15 minutes."

### What Happens:
- After 5 failed attempts, account is locked
- Lockout lasts 15 minutes
- Protects against brute-force attacks
- Failed attempts are logged
- Lockout time is shown to user

---

## Summary Checklist

After completing all steps, you should have screenshots for:

1. ✅ Landing page
2. ✅ Signup page (before submission)
3. ✅ Signup success
4. ✅ Login page (before submission)
5. ✅ Dashboard after login
6. ✅ Dashboard navigation
7. ✅ Dashboard action buttons
8. ✅ Mobile menu (optional)
9. ✅ Add customer form (before submission)
10. ✅ Customer added success
11. ✅ New case form (before submission)
12. ✅ Case created success
13. ✅ Case detail page
14. ✅ Document upload section
15. ✅ Event history timeline
16. ✅ Document upload form
17. ✅ Document uploaded success
18. ✅ Generate PDF button
19. ✅ Generated PDF
20. ✅ AI intake chat interface
21. ✅ AI conversation in progress
22. ✅ AI ready to submit
23. ✅ Case created from AI intake
24. ✅ Status check page (before submission)
25. ✅ Status check result
26. ✅ Reminders page
27. ✅ Reminder approval
28. ✅ Analytics dashboard
29. ✅ Analytics charts (zoom in)
30. ✅ Admin checklist page
31. ✅ Adding a service type
32. ✅ Adding a document requirement
33. ✅ Checklist after updates
34. ✅ Data deletion page
35. ✅ Delete confirmation modal
36. ✅ Deletion success
37. ✅ Audit log page
38. ✅ Audit log details (zoom in)
39. ✅ Add to home screen prompt (Android)
40. ✅ App icon on home screen
41. ✅ App in standalone mode
42. ✅ Offline mode
43. ✅ Logout button
44. ✅ Login page after logout
45. ✅ Forgot password page
46. ✅ Forgot password success
47. ✅ Reset password page
48. ✅ Password reset success
49. ✅ Account lockout message

---

## Tips for Good Screenshots

1. **Use High Resolution**: Take screenshots at your screen's native resolution
2. **Clean Browser**: Clear browser history/cookies before starting for a fresh experience
3. **Consistent Styling**: Use the same browser and zoom level for all screenshots
4. **Hide Personal Info**: Blur or crop sensitive information (emails, phone numbers)
5. **Include Context**: Show enough of the UI to understand the feature
6. **Label Screenshots**: Rename files to match the screenshot points (e.g., `01-landing-page.png`)
7. **Mobile Screenshots**: Use phone screenshots for PWA-related images
8. **PDF Screenshots**: Open PDF and screenshot the content

---

## Organizing Screenshots for README

Recommended folder structure:
```
screenshots/
├── 01-landing-page.png
├── 02-signup-page.png
├── 03-signup-success.png
├── 04-login-page.png
├── 05-dashboard.png
├── ...
└── 49-account-lockout.png
```

In your README.md, reference screenshots like:
```markdown
![Landing Page](screenshots/01-landing-page.png)
```

---

## Troubleshooting

### Issues During Testing

**Problem**: Signup fails with "Office code already exists"
- **Solution**: Use a different office code (must be unique)

**Problem**: Document upload fails
- **Solution**: Ensure R2 storage is configured in .env, or skip this step

**Problem**: AI intake doesn't respond
- **Solution**: Ensure GROQ_API_KEY is set in .env

**Problem**: Password reset email not received
- **Solution**: Ensure RESEND_API_KEY is set in .env and email is valid

**Problem**: Analytics shows no data
- **Solution**: Create some cases first to populate data

---

## Conclusion

This guide covers all major features of RTO Autopilot:
- ✅ Multi-tenant office management
- ✅ Case creation and tracking
- ✅ Document management
- ✅ AI-powered intake
- ✅ Analytics dashboard
- ✅ Admin functions (checklists, data deletion, audit log)
- ✅ Security features (account lockout, password reset)
- ✅ PWA installation for mobile

Follow each step, take the screenshots, and you'll have comprehensive documentation for your README!
