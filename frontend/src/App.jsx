import { Link, Route, Routes } from 'react-router-dom';
import AppLayout from './layouts/AppLayout';
import PublicLayout from './layouts/PublicLayout';
import Account from './pages/Account';
import Cases, { CaseDetail } from './pages/dashboard/Cases';
import Overview from './pages/dashboard/Overview';
import {
  Appointments, Clients, Consultations, Documents, Hearings, Invoices, LegalAid, Payments, Tasks, Users,
} from './pages/dashboard/Resources';
import { PortalAppointments, PortalCases, PortalDocuments, PortalHearings, PortalHome, PortalInvoices } from './pages/portal/Portal';
import Academy from './pages/public/Academy';
import Contact from './pages/public/Contact';
import { Consultation, LegalAidApply, LegalAidTrack } from './pages/public/Forms';
import Home from './pages/public/Home';
import Knowledge, { ArticleDetail, GuidedHelp } from './pages/public/Knowledge';
import Lawyers, { LawyerDetail } from './pages/public/Lawyers';
import Login from './pages/public/Login';
import PracticeAreas, { PracticeAreaDetail } from './pages/public/PracticeAreas';

function NotFound() {
  return (
    <section className="section center">
      <div className="container">
        <img src="/mark.png" alt="" style={{ height: 90, margin: '0 auto 20px' }} />
        <h1>Page not found</h1>
        <p className="lead">The page you are looking for does not exist.</p>
        <Link to="/" className="btn btn-primary">Back to home</Link>
      </div>
    </section>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route element={<PublicLayout />}>
        <Route index element={<Home />} />
        <Route path="practice-areas" element={<PracticeAreas />} />
        <Route path="practice-areas/:slug" element={<PracticeAreaDetail />} />
        <Route path="lawyers" element={<Lawyers />} />
        <Route path="lawyers/:id" element={<LawyerDetail />} />
        <Route path="consultation" element={<Consultation />} />
        <Route path="legal-aid" element={<LegalAidApply />} />
        <Route path="legal-aid/track" element={<LegalAidTrack />} />
        <Route path="legal-aid/track/:code" element={<LegalAidTrack />} />
        <Route path="knowledge" element={<Knowledge />} />
        <Route path="knowledge/guided" element={<GuidedHelp />} />
        <Route path="knowledge/articles/:slug" element={<ArticleDetail />} />
        <Route path="academy" element={<Academy />} />
        <Route path="contact" element={<Contact />} />
        <Route path="*" element={<NotFound />} />
      </Route>
      <Route path="/dashboard" element={<AppLayout area="firm" />}>
        <Route index element={<Overview />} />
        <Route path="consultations" element={<Consultations />} />
        <Route path="legal-aid" element={<LegalAid />} />
        <Route path="clients" element={<Clients />} />
        <Route path="cases" element={<Cases />} />
        <Route path="cases/:id" element={<CaseDetail />} />
        <Route path="hearings" element={<Hearings />} />
        <Route path="appointments" element={<Appointments />} />
        <Route path="tasks" element={<Tasks />} />
        <Route path="documents" element={<Documents />} />
        <Route path="invoices" element={<Invoices />} />
        <Route path="payments" element={<Payments />} />
        <Route path="users" element={<Users />} />
      </Route>
      <Route path="/portal" element={<AppLayout area="portal" />}>
        <Route index element={<PortalHome />} />
        <Route path="cases" element={<PortalCases />} />
        <Route path="hearings" element={<PortalHearings />} />
        <Route path="appointments" element={<PortalAppointments />} />
        <Route path="documents" element={<PortalDocuments />} />
        <Route path="invoices" element={<PortalInvoices />} />
      </Route>
      <Route path="/account" element={<AppLayout area="any" />}>
        <Route index element={<Account />} />
      </Route>
    </Routes>
  );
}
