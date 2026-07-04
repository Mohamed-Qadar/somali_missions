from django.test import TestCase
from django.contrib.auth.models import User
from missions.models import Mission, Complaint, UserProfile, ComplaintEvidence, EmbassyInvitation, SecureMessage, AuditLog
from missions.utils.ai_helpers import classify_complaint_ai

class EnhancedPlatformTests(TestCase):
    def setUp(self):
        self.mission = Mission.objects.create(name='Somali Embassy in London', country='UK', city='London')
        self.user = User.objects.create_user(username='citizen123', password='password123')

    def test_user_profile_created_automatically(self):
        # Verify that UserProfile is automatically created via the signal
        self.assertIsNotNone(self.user.profile)
        self.assertEqual(self.user.profile.role, UserProfile.Role.CITIZEN)
        self.assertEqual(self.user.profile.full_name, 'citizen123')

    def test_ai_classification_urgency_keywords(self):
        # Critical keywords
        res_crit = classify_complaint_ai("Assault problem", "A citizen is detained at the local jail and is beaten.")
        self.assertEqual(res_crit['priority'], 'CRITICAL')
        self.assertEqual(res_crit['department'], 'Emergency & Citizen Protection Division')

        # High keywords
        res_high = classify_complaint_ai("Bribe issue", "Embassy staff demands cash payment under the table for passport.")
        self.assertEqual(res_high['priority'], 'HIGH')
        self.assertEqual(res_high['department'], 'Internal Audit & Anti-Corruption Bureau')

        # Low/Default keywords
        res_low = classify_complaint_ai("Question", "What are the working hours of the consulate?")
        self.assertEqual(res_low['priority'], 'LOW')

    def test_complaint_auto_prioritization_on_save(self):
        # Verify that priority and suggested department are set on save
        c = Complaint.objects.create(
            mission=self.mission,
            subject="Arrested in Turkey",
            message="A Somali citizen was arrested and is in prison",
            rating=2,
            category="EMERGENCY"
        )
        self.assertEqual(c.priority, Complaint.Priority.CRITICAL)
        self.assertEqual(c.suggested_department, "Emergency & Citizen Protection Division")

    def test_satisfaction_survey_computations(self):
        c = Complaint.objects.create(
            mission=self.mission,
            subject="Visa delay",
            message="Serious delays on consular passport processing",
            rating=1,
            category="PASSPORT"
        )
        # Initially satisfaction is None
        self.assertNull = lambda x: self.assertIsNone(x)
        self.assertIsNone(c.satisfaction_rating)
        
        # citizen submits satisfaction survey
        c.satisfaction_rating = 4
        c.satisfaction_comment = "Resolution was quick after oversight alert."
        c.save()
        
        # Verify saved values
        db_complaint = Complaint.objects.get(pk=c.pk)
        self.assertEqual(db_complaint.satisfaction_rating, 4)
        self.assertEqual(db_complaint.satisfaction_comment, "Resolution was quick after oversight alert.")

    def test_embassy_invitation_and_activation(self):
        # Create invitation
        inv = EmbassyInvitation.objects.create(
            email='officer@somali.gov.so',
            mission=self.mission,
            role='EMBASSY_OFFICER',
            token='testtoken12345'
        )
        self.assertFalse(inv.is_used)

        # Post data to activation view
        response = self.client.post(f'/embassy/activate/{inv.token}/', {
            'username': 'newofficer',
            'full_name': 'Officer New',
            'password': 'officerpassword123',
            'confirm_password': 'officerpassword123'
        })
        self.assertEqual(response.status_code, 302)  # Should redirect to embassy dashboard
        
        # Verify user created and updated
        user = User.objects.get(username='newofficer')
        self.assertEqual(user.email, 'officer@somali.gov.so')
        self.assertEqual(user.profile.role, UserProfile.Role.EMBASSY_OFFICER)
        self.assertEqual(user.profile.mission, self.mission)
        self.assertEqual(user.profile.full_name, 'Officer New')
        self.assertTrue(user.profile.email_verified)
        
        # Verify invitation marked as used
        inv.refresh_from_db()
        self.assertTrue(inv.is_used)

    def test_secure_messaging_post(self):
        # Setup case and authenticated citizen user
        c = Complaint.objects.create(
            mission=self.mission,
            subject="Passport Delay",
            message="Please help me",
            rating=3,
            citizen_user=self.user
        )
        self.client.login(username='citizen123', password='password123')
        
        response = self.client.post(f'/embassy/case/{c.pk}/message/', {
            'message_text': 'I uploaded the documents. Please check.'
        })
        self.assertEqual(response.status_code, 302)
        
        # Verify message created in DB
        msg = SecureMessage.objects.filter(complaint=c).first()
        self.assertIsNotNone(msg)
        self.assertEqual(msg.message, 'I uploaded the documents. Please check.')
        self.assertEqual(msg.sender, self.user)
        self.assertEqual(msg.sender_type, SecureMessage.SenderType.CITIZEN)

        # Verify audit log was created
        log = AuditLog.objects.filter(complaint=c, action="Sent Secure Message").first()
        self.assertIsNotNone(log)

    def test_embassy_performance_monitoring_and_flagging(self):
        # Ministry Admin user
        admin_user = User.objects.create_user(username='admin_user', password='password123')
        admin_user.profile.role = UserProfile.Role.MINISTRY_ADMIN
        admin_user.profile.save()
        
        # Create 6 unresolved complaints with low satisfaction ratings for our mission
        for i in range(6):
            comp = Complaint.objects.create(
                mission=self.mission,
                subject=f"Bad service {i}",
                message="Rude staff",
                rating=1,
                satisfaction_rating=2,  # 2/5 stars is 40% (under 60%)
                status=Complaint.Status.SUBMITTED
            )
        
        # Get ministry operations view (as Admin)
        self.client.login(username='admin_user', password='password123')
        response = self.client.get('/ministry/operations/')
        self.assertEqual(response.status_code, 200)
        
        # Check if the mission was red-flagged in performance context
        embassy_perf = response.context['embassy_perf']
        mission_perf = next(p for p in embassy_perf if p['mission'] == self.mission)
        
        self.assertEqual(mission_perf['unresolved'], 6)
        self.assertEqual(mission_perf['satisfaction_rate'], 40.0)
        self.assertTrue(mission_perf['is_flagged'])
        self.assertContains(response, "RED ALERT")
