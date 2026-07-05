import LogoLoop, { type LogoItem } from './LogoLoop/LogoLoop';

const INSTITUTION_LOGOS: LogoItem[] = [
  { src: '/institution-logos/rtb.svg', alt: 'Residential Tenancies Board' },
  { src: '/institution-logos/citizens-info.svg', alt: 'Citizens Information' },
  { src: '/institution-logos/revenue-ie.png', alt: 'Revenue Commissioners' },
  { src: '/institution-logos/hse.png', alt: 'Health Service Executive' },
  { src: '/institution-logos/gov-ie.png', alt: 'gov.ie' },
  { src: '/institution-logos/nhs.svg', alt: 'National Health Service' },
  { src: '/institution-logos/hmrc.png', alt: 'HM Revenue & Customs' },
  { src: '/institution-logos/dvla.png', alt: 'Driver & Vehicle Licensing Agency' },
  { src: '/institution-logos/home-office.png', alt: 'UK Home Office' },
  { src: '/institution-logos/irs.svg', alt: 'Internal Revenue Service' },
  { src: '/institution-logos/ssa-full.png', alt: 'Social Security Administration' },
  { src: '/institution-logos/uscis.png', alt: 'US Citizenship & Immigration Services' },
  { src: '/institution-logos/fda.svg', alt: 'Food & Drug Administration' },
  { src: '/institution-logos/cms.svg', alt: 'Centers for Medicare & Medicaid Services' },
];

export default function InstitutionsMarquee() {
  return (
    <section
      aria-label="Institutions we support"
      className="bg-stone-900 py-10"
    >
      <div className="mx-auto mb-6 max-w-6xl px-5 sm:px-8">
        <h2 className="text-center text-sm font-semibold uppercase tracking-wider text-stone-400">
          Institutions we support
        </h2>
      </div>

      <div className="relative h-[100px] overflow-hidden">
        <LogoLoop
          logos={INSTITUTION_LOGOS}
          speed={100}
          direction="left"
          logoHeight={40}
          gap={60}
          hoverSpeed={0}
          scaleOnHover
          fadeOut
          fadeOutColor="#1c1917"
          ariaLabel="Institutions we support"
          className="logoloop--invert"
        />
      </div>
    </section>
  );
}
