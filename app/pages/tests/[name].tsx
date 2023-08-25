import Layout from '../../components/layout'
import { getAllPostIds, getPostData } from '../../lib/posts'
import { useRouter } from 'next/router'
import Head from 'next/head'
import Date from '../../components/date'
import utilStyles from '../../styles/utils.module.css'

export default function TestPost({ postData }) {
  return (
    <Layout>
      <Head>
        <title>{postData.title}</title>
      </Head>
      <article>
        <h1 className={utilStyles.headingXl}>{postData.title}</h1>
        <div className={utilStyles.lightText}>
          <Date dateString={postData.date} />
        </div>
        <div dangerouslySetInnerHTML={{ __html: postData.contentHtml }} />
      </article>
    </Layout>
  )
}

export async function getStaticPaths() {
  let paths = getAllPostIds();
  console.log(paths);
  paths = paths.map((path) => {
    path.params["name"] = path.params["id"]; 
    delete path.params["id"]; 
    return path;
  });
  console.log(paths);
  return {
    paths,
    fallback: false
  }
}

export async function getStaticProps({ params }) {
  const postData = await getPostData(params.name);
  return {
    props: {
      postData: {
        title: "Test Post",
        date: "2020-01-01",
        contentHtml: `<div>Testing ... ${postData.contentHtml}</div>`
      }
    }
  }
}
