import { createContext, useContext, useEffect, useMemo, useState } from 'react';
import { getLang, setLang as storeLang } from '../api/client';

const dict = {
  en: {
    home: 'Home', practice: 'Practice Areas', lawyers: 'Our Lawyers', legalAid: 'Legal Aid', knowledge: 'Knowledge',
    academy: 'Academy', contact: 'Contact', login: 'Log in', logout: 'Log out', dashboard: 'Dashboard', portal: 'My Portal',
    book: 'Book a Consultation', heroEyebrow: 'Anadi Law Firm · Dhaka', heroTitle: 'Counsel rooted in integrity,',
    heroTitle2: 'written for your future.',
    heroText: 'From family matters to corporate disputes, our advocates guide you with clarity, care and a steady hand — in English and Bangla.',
    exploreServices: 'Explore services', findHelp: 'Find the right help',
    whyTitle: 'Why clients trust Anadi', practiceTitle: 'Areas of practice', practiceSub: 'Focused expertise across the matters that shape lives and livelihoods.',
    lawyersTitle: 'Meet our advocates', lawyersSub: 'Experienced counsel who listen first.',
    viewAll: 'View all', learnMore: 'Learn more', years: 'years experience', languages: 'Languages',
    ctaTitle: 'Have a legal question?', ctaText: 'Tell us about your matter. A member of our team will contact you to arrange a consultation.',
    legalAidTitle: 'Legal aid for those who need it', legalAidText: 'Apply for assisted legal support and track your application privately with a secure code.',
    apply: 'Apply now', track: 'Track application', guided: 'Guided help', search: 'Search',
    name: 'Full name', phone: 'Phone', email: 'Email', message: 'Message', submit: 'Submit', sending: 'Sending…',
    preferredDate: 'Preferred date', preferredLanguage: 'Preferred language', area: 'Practice area',
    disclaimer: 'Information on this website is general and is not legal advice.',
    quickLinks: 'Quick links', reachUs: 'Reach us', hours: 'Working hours', address: 'Address',
    articles: 'Articles', faqs: 'FAQs', topics: 'Rights topics', courses: 'Courses', sessions: 'Live sessions', pathways: 'Pathways',
    register: 'Register', seatsLeft: 'seats left', allRights: 'All rights reserved.',
  },
  bn: {
    home: 'হোম', practice: 'সেবাসমূহ', lawyers: 'আমাদের আইনজীবী', legalAid: 'আইনি সহায়তা', knowledge: 'জ্ঞানভান্ডার',
    academy: 'একাডেমি', contact: 'যোগাযোগ', login: 'লগইন', logout: 'লগআউট', dashboard: 'ড্যাশবোর্ড', portal: 'আমার পোর্টাল',
    book: 'পরামর্শ বুক করুন', heroEyebrow: 'অনাদি ল ফার্ম · ঢাকা', heroTitle: 'সততায় প্রোথিত পরামর্শ,',
    heroTitle2: 'আপনার ভবিষ্যতের জন্য লেখা।',
    heroText: 'পারিবারিক বিষয় থেকে কর্পোরেট বিরোধ — আমাদের আইনজীবীরা স্বচ্ছতা ও যত্নের সাথে আপনাকে পথ দেখান, বাংলা ও ইংরেজিতে।',
    exploreServices: 'সেবাসমূহ দেখুন', findHelp: 'সঠিক সহায়তা খুঁজুন',
    whyTitle: 'কেন অনাদির উপর আস্থা', practiceTitle: 'আইনি সেবার ক্ষেত্র', practiceSub: 'জীবন ও জীবিকাকে প্রভাবিত করে এমন বিষয়ে বিশেষ দক্ষতা।',
    lawyersTitle: 'আমাদের আইনজীবীগণ', lawyersSub: 'অভিজ্ঞ আইনজীবী, যারা আগে শোনেন।',
    viewAll: 'সব দেখুন', learnMore: 'আরও জানুন', years: 'বছরের অভিজ্ঞতা', languages: 'ভাষা',
    ctaTitle: 'আইনি প্রশ্ন আছে?', ctaText: 'আপনার বিষয়টি জানান। আমাদের টিম পরামর্শের জন্য আপনার সাথে যোগাযোগ করবে।',
    legalAidTitle: 'প্রয়োজনে আইনি সহায়তা', legalAidText: 'সহায়তার জন্য আবেদন করুন এবং গোপন কোড দিয়ে আবেদনের অবস্থা দেখুন।',
    apply: 'আবেদন করুন', track: 'আবেদন ট্র্যাক করুন', guided: 'নির্দেশিত সহায়তা', search: 'খুঁজুন',
    name: 'পূর্ণ নাম', phone: 'ফোন', email: 'ইমেইল', message: 'বার্তা', submit: 'জমা দিন', sending: 'পাঠানো হচ্ছে…',
    preferredDate: 'পছন্দের তারিখ', preferredLanguage: 'পছন্দের ভাষা', area: 'সেবার ক্ষেত্র',
    disclaimer: 'এই ওয়েবসাইটের তথ্য সাধারণ তথ্য, আইনি পরামর্শ নয়।',
    quickLinks: 'দ্রুত লিংক', reachUs: 'যোগাযোগ করুন', hours: 'কর্মসময়', address: 'ঠিকানা',
    articles: 'প্রবন্ধ', faqs: 'প্রশ্নোত্তর', topics: 'অধিকার বিষয়', courses: 'কোর্স', sessions: 'লাইভ সেশন', pathways: 'শেখার পথ',
    register: 'নিবন্ধন', seatsLeft: 'আসন বাকি', allRights: 'সর্বস্বত্ব সংরক্ষিত।',
  },
};

const LangContext = createContext(null);

export function LangProvider({ children }) {
  const [lang, setLangState] = useState(getLang());
  useEffect(() => {
    document.documentElement.lang = lang;
    document.documentElement.dataset.lang = lang;
  }, [lang]);
  const value = useMemo(() => ({
    lang,
    setLang: (l) => { storeLang(l); setLangState(l); },
    t: (key) => dict[lang]?.[key] ?? dict.en[key] ?? key,
  }), [lang]);
  return <LangContext.Provider value={value}>{children}</LangContext.Provider>;
}

export const useLang = () => useContext(LangContext);
