import type {ReactNode} from 'react';
import clsx from 'clsx';
import Heading from '@theme/Heading';
import styles from './styles.module.css';

type FeatureItem = {
  title: string;
  Svg: React.ComponentType<React.ComponentProps<'svg'>>;
  description: ReactNode;
};

const FeatureList: FeatureItem[] = [
  {
    title: '🧩 LEGO-архитектура',
    Svg: require('@site/static/img/undraw_docusaurus_mountain.svg').default,
    description: (
      <>
        Собирайте свой стек из независимых компонентов. Легко меняйте реализации 
        интерфейсов (например, одну векторную БД на другую) одной командой.
      </>
    ),
  },
  {
    title: '🔗 Гибридная оркестрация',
    Svg: require('@site/static/img/undraw_docusaurus_tree.svg').default,
    description: (
      <>
        Единое управление Python-пакетами (через <code>uv</code>) и инфраструктурными 
        сервисами (через <code>docker compose</code>) в одном манифесте.
      </>
    ),
  },
  {
    title: '⚡ Атомарная синхронизация',
    Svg: require('@site/static/img/undraw_docusaurus_react.svg').default,
    description: (
      <>
        Транзакционное обновление конфигураций. Если зависимости не сошлись, 
        ваши рабочие файлы останутся в стабильном состоянии.
      </>
    ),
  },
];

function Feature({title, Svg, description}: FeatureItem) {
  return (
    <div className={clsx('col col--4')}>
      <div className="text--center">
        <Svg className={styles.featureSvg} role="img" />
      </div>
      <div className="text--center padding-horiz--md">
        <Heading as="h3">{title}</Heading>
        <p>{description}</p>
      </div>
    </div>
  );
}

export default function HomepageFeatures(): ReactNode {
  return (
    <section className={styles.features}>
      <div className="container">
        <div className="row">
          {FeatureList.map((props, idx) => (
            <Feature key={idx} {...props} />
          ))}
        </div>
      </div>
    </section>
  );
}
