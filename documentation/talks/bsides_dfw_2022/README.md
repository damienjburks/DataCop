BSides DFW 2022
---

This section of the repository contains the slide deck that I used to speak at [BSides DFW 2022](http://www.securitybsides.com/w/page/149758035/DFW_2022).
Information about the talk is listed below: 

- Title: `Minimizing AWS S3 attack vectors at scale`
- Abstract: 
>AWS provides services and third-party solutions, such as AWS Macie and Trend Micro, that can help us secure our S3 buckets and associated components. 
>Macie is a fully-managed data privacy and data security solution that provides customizable alerts and findings on sensitive data found in S3. 
>The downside is that it does not: 
>
>1. Auto-remediate threats and misconfigured S3 buckets
>2. Inspect and quarantine malicious files (malware, ransomware, etc.) 
>
>Therefore, the security engineer must figure out how to overcompensate for these missed features by scanning each file to determine whether it is malicious using CloudOne and by inspecting Macie's findings report. 
>The key issue, however, is that the engineer would have to manually undertake remediation actions. 
>
>In this talk, I will discuss the pre-existing gap and the open-source solution known as DataCop. 
>I'll also break down the architecture of DataCop, which will consist of: 
>
>1. Utilized Services (AWS Macie, S3, Trend Micro Cloud One)
>2. S3 Remediation Actions - entire process and flow 
>3. IAM Considerations
>4. Language and Development Kits
>
>Following the architectural deep-dive, there will be more information on the value added to existing processes if this solution were to be adopted. 
>To conclude, those who attend this talk will leave with practical knowledge on automating the remediation of S3 buckets on Macie's and Trend Micro Cloud One's findings.

- Slide Deck: [BSides DFW Final Deck](bsides_dfw_2022_preso_final.pptx)
- YouTube Video: [Minimizing AWS S3 attack vectors at scale](https://www.youtube.com/watch?v=-vIJBvUA4hI)

**PSA:** This was my second talk that I've given in person, and I can say it was the most engaging talk.